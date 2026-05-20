"""URL routes for the trainer app."""
from django.urls import path

from . import views


app_name = "trainer"

urlpatterns = [
    path("", views.PageSchemaListView.as_view(), name="page_list"),
    path("pages/create/", views.PageSchemaCreateView.as_view(), name="page_create"),
    path("pages/<int:pk>/", views.PageSchemaDetailView.as_view(), name="page_detail"),
    path("pages/<int:pk>/edit/", views.PageSchemaUpdateView.as_view(), name="page_edit"),
    path("pages/<int:pk>/delete/", views.PageSchemaDeleteView.as_view(), name="page_delete"),
]
