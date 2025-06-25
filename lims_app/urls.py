from django.urls import path
from .views import (
    home, readers_tab, books_list, my_bag_tab,
    process_checkout, add_remove_book_to_bag,
    returns_page, return_loan,reader_search_api
)

urlpatterns = [
    path('', home, name='home'),
    path('readers/', readers_tab, name='readers_tab'),
    path('books/', books_list, name='books_list'),
    path('mybag/', my_bag_tab, name='my_bag_tab'),
    path('mybag/add_remove/<int:book_id>/', add_remove_book_to_bag, name='add_remove_book_to_bag'),
    path('mybag/checkout/', process_checkout, name='process_checkout'),
    path('returns/', returns_page, name='returns_page'),
    path('returns/return_loan/<int:loan_id>/', return_loan, name='return_loan'),
    path('api/reader_search/', reader_search_api, name='reader_search_api'),

]
