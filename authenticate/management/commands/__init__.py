from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from authenticate.models import UserProfile

class Command(BaseCommand):
    def handle(self, *args, **options):
        users = User.objects.filter(userprofile__isnull=True)
        for user in users:
            UserProfile.objects.create(user=user)
            self.stdout.write(f'Created profile for user: {user.username}')
