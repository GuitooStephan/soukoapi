from django.core.management.base import BaseCommand
from main.models import UserProfile

class Command(BaseCommand):
	def handle(self, *args, **options):
		if not UserProfile.objects.filter(email="admin@admin.com").exists():
			UserProfile.objects.create_superuser(email="admin@admin.com", password="password")