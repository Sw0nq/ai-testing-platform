"""Admin configuration for the trainer app."""
from django.contrib import admin

from .models import FieldSchema, PageSchema, TestCase, TestRun


@admin.register(PageSchema)
class PageSchemaAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "description", "created_by__username")
    readonly_fields = ("created_at",)


@admin.register(FieldSchema)
class FieldSchemaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "label",
        "page",
        "field_type",
        "is_required",
        "order",
    )
    list_filter = ("field_type", "is_required", "page")
    search_fields = ("name", "label", "page__name", "custom_rules")


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "page",
        "test_type",
        "priority",
        "generation_batch",
        "created_at",
    )
    list_filter = ("test_type", "priority", "created_at", "page")
    search_fields = ("title", "expected_result", "page__name", "generation_batch")
    readonly_fields = ("generation_batch", "created_at")


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ("test_case", "user", "status", "executed_at")
    list_filter = ("status", "executed_at")
    search_fields = ("test_case__title", "user__username", "notes")
    readonly_fields = ("executed_at",)
