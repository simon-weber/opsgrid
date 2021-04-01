# https://gist.github.com/konstin/124aa0cea03df4cfa7e85b6a191dffa1

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Syncs the Google SocialApp to the database."

    def handle(self, *args, **options):
        row, created = SocialApp.objects.update_or_create(
            provider="google",
            defaults={
                "name": "Google",
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "secret": settings.GOOGLE_OAUTH_SECRET,
            },
        )

        row.sites.set([settings.SITE_ID])

        if created:
            message = "Created social app: {}"
        else:
            message = "Updated social app: {}"
        self.stdout.write(self.style.SUCCESS(message.format("google")))
