from django.urls import path
from . import views

urlpatterns = [
    path('', views.ResidentListCreateView.as_view(), name='resident-list-create'),
    path('<int:pk>/', views.ResidentDetailView.as_view(), name='resident-detail'),
    path('profile/', views.MyResidentProfileView.as_view(), name='my-resident-profile'),
    path('search/', views.search_residents, name='search-residents'),
    path('stats/', views.resident_stats, name='resident-stats'),
]