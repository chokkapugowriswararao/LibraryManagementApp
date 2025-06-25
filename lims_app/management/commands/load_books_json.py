# lims_app/management/commands/load_books_json.py

import json
from datetime import datetime, date # Import date for handling year as a date
from django.core.management.base import BaseCommand
from lims_app.models import Book # Assuming 'lims_app' is your app name

class Command(BaseCommand):
    help = 'Load books from a new books.json format (compatible with "year" and "link" fields).'

    def handle(self, *args, **kwargs):
        # --- IMPORTANT: Update this path to your large JSON file ---
        # If your 1 lakh JSON file is named differently, change this.
        json_file_path = 'lims_app/books.json' # Example: 'lims_app/your_1_lakh_books.json'
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: JSON file not found at {json_file_path}."))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Error: Could not decode JSON from {json_file_path}. Check file format for errors."))
            return

        # Assuming your new 1 lakh JSON is an array of book objects directly at the root, like:
        # [ {book1}, {book2}, ... ]
        books_data_list = data 
        
        # If your new 1 lakh JSON is still structured like your OLD one (e.g., {"books": [...]})
        # then uncomment the line below and comment out the `books_data_list = data` line:
        # books_data_list = data.get('books', [])


        objs = []
        for book_entry in books_data_list:
            # --- Map JSON fields to Book model fields ---
            
            # Required fields - provide empty string default for get(), then validate
            title = book_entry.get('title', '')
            author = book_entry.get('author', '')

            if not title or not author:
                self.stderr.write(self.style.WARNING(f"Skipping book due to missing required field (title or author): {book_entry.get('title', 'N/A')} by {book_entry.get('author', 'N/A')}"))
                continue # Skip this entry if title or author is missing

            # published_date (Convert 'year' to a date object)
            published_year = book_entry.get('year')
            published_date = None
            if isinstance(published_year, int):
                # Handle potential negative years (BC) by taking absolute value
                # And setting it to Jan 1st of that year for simplicity
                try:
                    published_date = date(abs(published_year), 1, 1) 
                except ValueError: # Catches years like 0 or excessively large/small
                    self.stderr.write(self.style.WARNING(f"Invalid year '{published_year}' for book '{title}'. Setting published_date to None."))
            else:
                self.stderr.write(self.style.WARNING(f"Year is not an integer for book '{title}'. Setting published_date to None."))


            # website (Maps from 'link') - Remove trailing newline if present
            website = book_entry.get('link') 
            if website and isinstance(website, str):
                website = website.strip() # Removes whitespace, including newlines


            # pages (Direct match, allow None if not found or invalid)
            pages = book_entry.get('pages', None)
            if pages is not None:
                try:
                    pages = int(pages)
                except (ValueError, TypeError):
                    pages = None
                    self.stderr.write(self.style.WARNING(f"Invalid pages value for '{title}'. Setting pages to None."))


            # Fields missing in your new JSON, set to None if your model allows null=True, blank=True
            # OR provide a default string if your model field is NOT nullable.
            # I will assume `publisher` should be nullable now, based on previous discussion.
            isbn = book_entry.get('isbn', None)
            subtitle = book_entry.get('subtitle', None)
            description = book_entry.get('description', None)
            
            # --- IMPORTANT: publisher field ---
            # Your new JSON structure DOES NOT have a 'publisher' field.
            # If your Book model's 'publisher' field is:
            #   publisher = models.CharField(max_length=200, null=True, blank=True) -> Use `publisher = None` or `book_entry.get('publisher', None)`
            # If your Book model's 'publisher' field is:
            #   publisher = models.CharField(max_length=200) -> Use `publisher = "Unknown"` or some default string.
            # I will provide a default 'Unknown' here, but it's best to make it nullable if missing in your data.
            publisher = book_entry.get('publisher', 'Unknown') 
            # If you made `publisher` null/blank in models.py, you can use:
            # publisher = book_entry.get('publisher', None)

            # Create Book object
            objs.append(Book(
                isbn=isbn,
                title=title,
                subtitle=subtitle,
                author=author,
                published_date=published_date,
                publisher=publisher, # Using 'Unknown' or None if you make it nullable
                pages=pages,
                description=description,
                website=website
            ))

        # Use bulk_create for efficiency. ignore_conflicts=True will prevent errors
        # if you re-run the command and encounter duplicate ISBNs (if ISBNs are present).
        # If your data has no ISBNs or they are not unique, remove ignore_conflicts.
        Book.objects.bulk_create(objs, ignore_conflicts=True) 
        self.stdout.write(self.style.SUCCESS(f"Successfully loaded or updated {len(objs)} books."))