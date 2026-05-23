"""
Management command to create an admin user non-interactively.
Useful for Docker entrypoints and CI seed scripts.

Usage:
    python manage.py create_admin \\
        --email admin@nexusflow.com \\
        --username admin \\
        --password secret123 \\
        --first-name "System" \\
        --last-name "Admin"
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Create a NexusFlow admin user (non-interactive)"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Admin email address")
        parser.add_argument("--username", required=True, help="Username")
        parser.add_argument("--password", required=True, help="Password (min 8 chars)")
        parser.add_argument("--first-name", default="System", dest="first_name")
        parser.add_argument("--last-name", default="Admin", dest="last_name")

    def handle(self, *args, **options):
        email = options["email"]
        username = options["username"]
        password = options["password"]

        if len(password) < 8:
            raise CommandError("Password must be at least 8 characters.")

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f"User with email '{email}' already exists. Skipping.")
            )
            return

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=options["first_name"],
            last_name=options["last_name"],
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
            is_email_verified=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user created: {user.email} (id={user.pk})"
            )
        )
