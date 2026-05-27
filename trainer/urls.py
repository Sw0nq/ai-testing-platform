"""URL routes for the trainer app."""
from django.urls import path

from . import views


app_name = "trainer"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/stats/", views.user_stats_view, name="user_stats"),
    path("", views.PageSchemaListView.as_view(), name="page_list"),
    path("pages/create/", views.PageSchemaCreateView.as_view(), name="page_create"),
    path("pages/<int:pk>/", views.PageSchemaDetailView.as_view(), name="page_detail"),
    path("pages/<int:pk>/sandbox/", views.SandboxView.as_view(), name="sandbox"),
    path(
        "pages/<int:pk>/generate/",
        views.page_generate_test_cases,
        name="page_generate_test_cases",
    ),
    path(
        "pages/<int:pk>/public-analytics/",
        views.public_form_analytics_view,
        name="public_form_analytics",
    ),
    path(
        "pages/<int:pk>/enable-bugs/",
        views.enable_bugs_view,
        name="enable_bugs",
    ),
    path(
        "pages/<int:pk>/regenerate-bugs/",
        views.regenerate_bugs_view,
        name="regenerate_bugs",
    ),
    path(
        "pages/<int:pk>/disable-bugs/",
        views.disable_bugs_view,
        name="disable_bugs",
    ),
    path(
        "pages/<int:pk>/test-runs/create/",
        views.test_run_create_view,
        name="test_run_create",
    ),
    path(
        "pages/<int:page_id>/test-runs/<int:session_id>/",
        views.test_run_execute_view,
        name="test_run_execute",
    ),
    path("pages/<int:pk>/edit/", views.PageSchemaUpdateView.as_view(), name="page_edit"),
    path("pages/<int:pk>/delete/", views.PageSchemaDeleteView.as_view(), name="page_delete"),
    path(
        "pages/<int:page_id>/fields/<int:field_id>/edit/",
        views.FieldSchemaUpdateView.as_view(),
        name="field_edit",
    ),
    path(
        "pages/<int:page_id>/fields/<int:field_id>/delete/",
        views.FieldSchemaDeleteView.as_view(),
        name="field_delete",
    ),
]
