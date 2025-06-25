from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages


from .models import reader, Book, BagItem,Loan # Import BagItem
from django.db.models import Q
from django.core.paginator import Paginator
from django import forms
from datetime import datetime, date, timedelta # Import timedelta for return date logic
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponseBadRequest

# --- Book Form Definition ---
class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['isbn', 'title', 'subtitle', 'author', 'published_date', 'publisher', 'pages', 'description', 'website']
        widgets = {
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ISBN (optional)'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Book Title'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subtitle (optional)'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author Name'}),
            'published_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Publisher'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of Pages (optional)'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Book Description (optional)'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Website URL (optional)'}),
        }

def home(request):
    """Renders the home page."""
    return render(request, "home.html", {"current_tab": "home"})

def readers_tab(request):
    """
    Handles reader creation and displays a list of readers with search functionality.
    """
    if request.method == "POST":
        name = request.POST.get("reader_name")
        contact = request.POST.get("reader_contact")
        reference_id = request.POST.get("referece_id")
        address = request.POST.get("reader_address")

        if name and contact and reference_id and address:
            reader.objects.create(
                reader_name=name,
                reader_contact=contact,
                referece_id=reference_id,
                reader_address=address,
                active=True
            )
        return redirect("readers_tab")

    search_query = request.GET.get("search")
    if search_query and search_query.strip() != "":
        readers = reader.objects.filter(
            Q(reader_name__icontains=search_query) |
            Q(reader_contact__icontains=search_query) |
            Q(referece_id__icontains=search_query),
            active=True
        )
    else:
        readers = reader.objects.filter(active=True)

    return render(request, "readers.html", {
        "current_tab": "readers",
        "readers": readers,
        "search_query": search_query or ""
    })

def books_list(request):
    """
    Displays a list of books with search and pagination.
    Also handles adding new books via the modal and identifies books
    already in the user's bag based on session.
    """
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                # from django.contrib import messages
                # messages.success(request, "Book added successfully!")
                return redirect('books_list')
            except Exception as e:
                # messages.error(request, f"Error adding book: {e}")
                pass
    else:
        form = BookForm()

    search_query = request.GET.get('search', '')
    if search_query:
        books = Book.objects.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(publisher__icontains=search_query)
        ).order_by('title')
    else:
        books = Book.objects.all().order_by('title')

    paginator = Paginator(books, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- Bag functionality for books_list ---
    # Ensure a session key exists for the current user's bag
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    # Get IDs of books already in the current session's bag for UI feedback
    bagged_book_ids = BagItem.objects.filter(session_key=session_key).values_list('book__id', flat=True)

    return render(request, 'books.html', {
        'books': page_obj,
        'search_query': search_query,
        'current_tab': 'books',
        'form': form,
        'page_obj': page_obj,
        'bagged_book_ids': list(bagged_book_ids), # Convert to list for easy 'in' check in template
    })

@require_POST
def add_remove_book_to_bag(request, book_id):
    """
    AJAX endpoint to add or remove a book from the user's session-based bag.
    """
    book = get_object_or_404(Book, id=book_id)
    
    # Ensure session is active
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    bag_item = BagItem.objects.filter(book=book, session_key=session_key).first()

    if bag_item:
        bag_item.delete()
        action = 'removed'
        status_code = 200
    else:
        BagItem.objects.create(book=book, session_key=session_key)
        action = 'added'
        status_code = 201

    return JsonResponse({'status': 'success', 'action': action, 'book_id': book_id}, status=status_code)

def my_bag_tab(request):
    # Ensure session key exists
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    bag_items = BagItem.objects.filter(session_key=session_key).select_related('book').order_by('-added_at')
    readers_list = reader.objects.filter(active=True).order_by('reader_name')

    now = timezone.localtime()
    start_date_default = now.strftime('%Y-%m-%dT%H:%M')
    two_weeks_later = now + timedelta(days=14)
    return_date_default = two_weeks_later.strftime('%Y-%m-%dT%H:%M')

    context = {
        'current_tab': 'my_bag',
        'bag_items': bag_items,
        'readers_list': readers_list,
        'start_date_default': start_date_default,
        'return_date_default': return_date_default,
    }
    return render(request, 'my_bag.html', context)


@require_POST
def process_checkout(request):
    reader_id_input = request.POST.get('reader_id', '').strip()
    start_date_str = request.POST.get('start_date', '').strip()
    return_date_str = request.POST.get('return_date', '').strip()

    # Preserve entered form data for error redisplay
    form_data = {
        'reader_id': reader_id_input,
        'start_date': start_date_str,
        'return_date': return_date_str,
        'reader_name': request.POST.get('reader_name', '').strip(),
        'reader_contact': request.POST.get('reader_contact', '').strip(),
    }

    if not (reader_id_input and start_date_str and return_date_str):
        error_message = "Please fill all required fields: Reference ID, Start Date, and Return Date."
        return _render_my_bag_with_error(request, error_message, form_data)

    try:
        selected_reader = reader.objects.get(referece_id=reader_id_input)
    except reader.DoesNotExist:
        error_message = f"No reader found with Reference ID: {reader_id_input}"
        return _render_my_bag_with_error(request, error_message, form_data)

    # Parse dates in ISO format expected from datetime-local inputs
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        due_date = datetime.strptime(return_date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        error_message = "Invalid date format. Please select valid start and return dates."
        return _render_my_bag_with_error(request, error_message, form_data)

    session_key = request.session.session_key
    bag_items = BagItem.objects.filter(session_key=session_key).select_related('book')

    if not bag_items.exists():
        error_message = "Your bag is empty. Please add some books before checkout."
        return _render_my_bag_with_error(request, error_message, form_data)

    for item in bag_items:
        Loan.objects.create(
            reader=selected_reader,
            book=item.book,
            start_date=start_date,
            due_date=due_date,
            returned=False,
        )

    bag_items.delete()
    messages.success(request, "Checkout successful!")
    return redirect('returns_page')


def _render_my_bag_with_error(request, error_message, form_data):
    # Helper to render my_bag.html with error and filled form data
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    bag_items = BagItem.objects.filter(session_key=session_key).select_related('book').order_by('-added_at')
    readers_list = reader.objects.filter(active=True).order_by('reader_name')

    context = {
        'current_tab': 'my_bag',
        'bag_items': bag_items,
        'readers_list': readers_list,
        'error_message': error_message,
        'form_data': form_data,
    }
    return render(request, 'my_bag.html', context)

from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Loan  # Ensure Loan model exists
def returns_page(request):
    loans = Loan.objects.filter(returned=False).select_related('reader')
    return render(request, 'returns.html', {'loans': loans})

@require_POST
def return_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    loan.returned = True
    loan.save()
    return redirect('returns_page')
from .models import reader

@csrf_exempt
def reader_search_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ref_id = data.get('reference_id', '').strip()
            name = data.get('name', '').strip()
            contact = data.get('contact', '').strip()

            readers = reader.objects.all()

            if ref_id:
                readers = readers.filter(referece_id__iexact=ref_id)  # note spelling
            if name:
                readers = readers.filter(reader_name__icontains=name)
            if contact:
                readers = readers.filter(reader_contact__icontains=contact)

            if readers.exists():
                r = readers.first()
                return JsonResponse({
                    'found': True,
                    'reference_id': r.referece_id,
                    'name': r.reader_name,
                    'contact': r.reader_contact,
                })
            else:
                return JsonResponse({'found': False})

        except Exception as e:
            return JsonResponse({'found': False, 'error': str(e)})

    return JsonResponse({'found': False, 'error': 'Invalid request method'})
