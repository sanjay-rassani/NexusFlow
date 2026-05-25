"""
Wipe all application data so the database can start fresh.

Deletes every row from every table (schema and migrations are preserved),
clears the Redis cache, and removes uploaded media files.

Usage:
    python manage.py flush_all_data
    python manage.py flush_all_data --no-input
    python manage.py flush_all_data --no-input --keep-media
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Delete ALL data from the database, cache, and uploaded media"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Skip the confirmation prompt.",
        )
        parser.add_argument(
            "--keep-media",
            action="store_true",
            help="Do not delete files under MEDIA_ROOT.",
        )

    def handle(self, *args, **options):
        keep_media = options["keep_media"]

        if not options["no_input"]:
            targets = ["the entire database", "the Redis cache"]
            if not keep_media:
                targets.append("all uploaded media files")
            self.stdout.write(
                self.style.WARNING(
                    "This will permanently delete " + ", ".join(targets) + "."
                )
            )
            confirm = input("Type 'yes' to continue: ")
            if confirm != "yes":
                raise CommandError("Aborted.")

        self.stdout.write("Flushing database...")
        call_command("flush", interactive=False, verbosity=options.get("verbosity", 1))

        self.stdout.write("Clearing cache...")
        cache.clear()

        if not keep_media:
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                removed = 0
                for item in media_root.iterdir():
                    if item.name == ".gitkeep":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    removed += 1
                if removed:
                    self.stdout.write(
                        self.style.SUCCESS(f"Cleared {removed} item(s) from {media_root}")
                    )
                else:
                    self.stdout.write(f"No media files to remove in {media_root}")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. All data deleted — run create_admin (and seed scripts) to repopulate."
            )
        )
