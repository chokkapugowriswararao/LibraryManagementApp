from django.contrib import admin
from .models import Book, reader  # explicitly import your models

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publisher', 'published_date', 'pages')
    search_fields = ('title', 'author', 'publisher', 'isbn')

# Register reader if you want:
admin.site.register(reader)
