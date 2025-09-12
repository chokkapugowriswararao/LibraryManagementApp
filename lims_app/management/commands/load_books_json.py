import json
from datetime import date
from django.core.management.base import BaseCommand
from lims_app.models import Book # Make sure 'lims_app' is your correct app name

class Command(BaseCommand):
    help = 'Loads books from a JSON file into the database, preventing duplicates.'

    # THIS IS THE CRITICAL PART THAT WAS MISSING.
    # It tells Django that this command accepts one argument.
    def add_arguments(self, parser):
        parser.add_argument('json_file_path', type=str, help='The full path to the JSON file to load.')

    # The 'handle' function now uses 'options' to get the argument.
    def handle(self, *args, **options):
        json_file_path = options['json_file_path']
        self.stdout.write(self.style.SUCCESS(f"Starting to load books from: {json_file_path}"))

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                books_data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: The file at {json_file_path} was not found."))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR("Error: Could not decode JSON. Please check the file for formatting errors."))
            return

        created_count = 0
        skipped_count = 0

        for entry in books_data:
            title = entry.get('title', '').strip()
            author = entry.get('author', '').strip()

            if not title or not author:
                skipped_count += 1
                continue

            published_date = None
            year = entry.get('year')
            if isinstance(year, int) and year != 0:
                try:
                    published_date = date(abs(year), 1, 1)
                except (ValueError, TypeError):
                    pass # Ignore invalid years

            # Use update_or_create to prevent duplicates based on title and author
            # This is safer and more explicit than get_or_create for this task.
            obj, created = Book.objects.update_or_create(
                title=title,
                author=author,
                defaults={
                    'published_date': published_date,
                    'pages': entry.get('pages'),
                    'website': entry.get('link', '').strip() or None,
                    'publisher': entry.get('publisher') # Will be None if not present
                }
            )

            if created:
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"\n--- Import Complete ---"))
        self.stdout.write(f"Successfully created {created_count} new books.")
        self.stdout.write(f"Found and updated/skipped {len(books_data) - created_count - skipped_count} existing books.")
        self.stdout.write(f"Skipped {skipped_count} entries due to missing data.")
