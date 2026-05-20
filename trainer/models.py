"""Database models for the trainer app."""
import uuid

from django.conf import settings
from django.db import models


class PageSchema(models.Model):
    """A user-created web form/page schema used for test generation."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="page_schemas",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self) -> str:
        return self.name


class FieldSchema(models.Model):
    """A single input field definition within a page schema."""

    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        EMAIL = "email", "Email"
        DATE = "date", "Date"
        SELECT = "select", "Select"

    page = models.ForeignKey(
        PageSchema,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    is_required = models.BooleanField(default=False)
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    custom_rules = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["page", "order", "name"]

    def __str__(self) -> str:
        return f"{self.page}: {self.label}"


class TestCase(models.Model):
    """A generated or manually defined test case for a page schema."""

    class TestType(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"
        BOUNDARY = "boundary", "Boundary"

    class Priority(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    page = models.ForeignKey(
        PageSchema,
        on_delete=models.CASCADE,
        related_name="test_cases",
    )
    generation_batch = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    input_data = models.JSONField(default=dict)
    expected_result = models.TextField()
    test_type = models.CharField(max_length=20, choices=TestType.choices)
    priority = models.CharField(max_length=20, choices=Priority.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "priority", "title"]

    def __str__(self) -> str:
        return self.title


class TestRun(models.Model):
    """A user's execution result for a test case."""

    class Status(models.TextChoices):
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_runs",
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    notes = models.TextField(blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]

    def __str__(self) -> str:
        return f"{self.test_case} - {self.get_status_display()}"
