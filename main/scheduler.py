# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

import json
from heapq import heappop, heappush

from celery.beat import event_t
from celery.schedules import schedstate
from django_celery_beat.schedulers import DatabaseScheduler

from soukoapi.celery import app


def is_task_in_queue(task, queue_name=None):
    queues = [queue_name] if queue_name else app.amqp.queues.keys()

    for queue in queues:
        if task in get_celery_queue_tasks(queue):
            return True
    return False


def get_celery_queue_tasks(queue_name):
    with app.pool.acquire(block=True) as conn:
        tasks = conn.default_channel.client.lrange(queue_name, 0, -1)
        decoded_tasks = []

    for task in tasks:
        j = json.loads(task)
        task = j["headers"]["task"]
        if task not in decoded_tasks:
            decoded_tasks.append(task)
    return decoded_tasks


class SmartScheduler(DatabaseScheduler):
    """
    Smart means that prevents duplicating of tasks in queues.

    The aim is to execute tasks only once.
    """

    def is_due(self, entry):
        is_due, next_time_to_run = entry.is_due()

        if not is_due or not is_task_in_queue(  # duplicate wouldn't be created
            entry.task
        ):  # not in queue so let it run
            return schedstate(is_due, next_time_to_run)

        # Task should be run (is_due) and it is present in queue (is_task_in_queue)
        H = self._heap

        if not H:
            return schedstate(False, self.max_interval)

        event = H[0]
        verify = heappop(H)
        if verify is event:
            next_entry = self.reserve(entry)
            heappush(
                H,
                event_t(self._when(next_entry, next_time_to_run), event[1], next_entry),
            )
        else:
            heappush(H, verify)
            next_time_to_run = min(verify[0], next_time_to_run)
        return schedstate(False, min(next_time_to_run, self.max_interval))
