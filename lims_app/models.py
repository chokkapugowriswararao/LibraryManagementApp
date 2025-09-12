from django.db import models

# Create your models here.
class reader(models.Model):
    referece_id = models.CharField(max_length=200)
    reader_name = models.CharField(max_length=200)
    reader_contact = models.CharField(max_length=200)
    reader_address = models.TextField()
    active  = models.BooleanField(default=True)
    def __str__(self):
        return str(self.reader_name)

class Book(models.Model):
    isbn = models.CharField(max_length=20, unique=True, null=True, blank=True)
    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=300, null=True, blank=True)
    author = models.CharField(max_length=200)
    published_date = models.DateField(null=True, blank=True)
    publisher = models.CharField(max_length=200, null=True, blank=True) # Made nullable
    pages = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.title

# --- NEW MODEL FOR BAG FUNCTIONALITY ---
class BagItem(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='bag_items')
    # Using session_key for unauthenticated users' bags.
    # If you implement user authentication, you might link to a User model instead.
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.book.title} (Bag ID: {self.session_key[:5] if self.session_key else 'N/A'})"

    class Meta:
        # Ensures a book can only be added once per unique session (or user)
        unique_together = ('book', 'session_key')
        verbose_name = "Bag Item"
        verbose_name_plural = "Bag Items"

from django.utils import timezone

class Loan(models.Model):
    reader = models.ForeignKey(reader, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    returned = models.BooleanField(default=False)
    returned_date = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"{self.book.title} loaned to {self.reader.reader_name}"