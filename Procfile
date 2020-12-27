release: python manage.py migrate
worker: python manage.py run-worker
beat: celery -A soukoapi beat -l info --scheduler main.scheduler.SmartScheduler --pidfile=
web: gunicorn soukoapi.wsgi
