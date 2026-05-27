"""Forms for the trainer app."""
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import FieldSchema, PageSchema, TestCase, TestRunResult, TestRunSession


class RegisterForm(UserCreationForm):
    """Registration form with Russian labels and help text."""

    username = forms.CharField(
        label="Имя пользователя",
        help_text="Обязательное поле. Не более 150 символов: буквы, цифры и @/./+/-/_.",
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
    )
    password1 = forms.CharField(
        label="Пароль",
        help_text="Пароль не должен быть слишком похож на ваши данные, слишком простым или полностью числовым.",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        help_text="Введите тот же пароль еще раз для проверки.",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )


class LoginForm(AuthenticationForm):
    """Login form with Russian labels."""

    username = forms.CharField(
        label="Имя пользователя",
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )


class PageSchemaForm(forms.ModelForm):
    """Form for creating and updating page schemas."""

    class Meta:
        model = PageSchema
        fields = ("name", "description")
        labels = {
            "name": "Название страницы",
            "description": "Описание",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Название страницы",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Краткое описание",
                    "rows": 5,
                }
            ),
        }


class FieldSchemaForm(forms.ModelForm):
    """Form for creating and updating fields inside a page schema."""

    class Meta:
        model = FieldSchema
        fields = (
            "name",
            "label",
            "field_type",
            "is_required",
            "min_length",
            "max_length",
            "custom_rules",
            "order",
        )
        labels = {
            "name": "Системное имя",
            "label": "Метка поля",
            "field_type": "Тип поля",
            "is_required": "Обязательное поле",
            "min_length": "Минимальная длина",
            "max_length": "Максимальная длина",
            "custom_rules": "Дополнительные правила",
            "order": "Порядок",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "first_name",
                }
            ),
            "label": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Имя пользователя",
                }
            ),
            "field_type": forms.Select(attrs={"class": "form-control"}),
            "is_required": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "min_length": forms.NumberInput(attrs={"class": "form-control"}),
            "max_length": forms.NumberInput(attrs={"class": "form-control"}),
            "custom_rules": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            raise forms.ValidationError(
                "Имя может содержать только латинские буквы, цифры и символ подчеркивания."
            )
        return name

    def clean(self):
        cleaned_data = super().clean()
        field_type = cleaned_data.get("field_type")
        min_length = cleaned_data.get("min_length")
        max_length = cleaned_data.get("max_length")

        if min_length is not None and max_length is not None and min_length > max_length:
            raise forms.ValidationError(
                "Минимальная длина не может быть больше максимальной."
            )

        length_fields_are_set = min_length is not None or max_length is not None
        length_supported_types = {
            FieldSchema.FieldType.TEXT,
            FieldSchema.FieldType.EMAIL,
        }
        if length_fields_are_set and field_type not in length_supported_types:
            raise forms.ValidationError(
                "Ограничения длины можно использовать только для текстовых и email-полей."
            )

        return cleaned_data


class DynamicSandboxForm(forms.Form):
    """Runtime form generated from FieldSchema objects for a PageSchema."""

    SELECT_CHOICES = (
        ("option_1", "Option 1"),
        ("option_2", "Option 2"),
        ("option_3", "Option 3"),
    )

    def __init__(self, page_schema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_schema = page_schema

        for field_schema in page_schema.fields.order_by("order", "id"):
            self.fields[field_schema.name] = self._build_field(field_schema)

    def _is_password_field(self, field_schema):
        field_name = field_schema.name.lower()
        return any(token in field_name for token in ("password", "pass", "pwd"))

    def _text_widget(self, field_schema):
        attrs = {"class": "form-control"}
        if self._is_password_field(field_schema):
            return forms.PasswordInput(attrs=attrs)
        if len(field_schema.custom_rules) > 100:
            return forms.Textarea(attrs={**attrs, "rows": 4})
        return forms.TextInput(attrs=attrs)

    def _email_widget(self, field_schema):
        attrs = {"class": "form-control"}
        if self._is_password_field(field_schema):
            return forms.PasswordInput(attrs=attrs)
        return forms.EmailInput(attrs=attrs)

    def _build_field(self, field_schema):
        common_options = {
            "label": field_schema.label,
            "required": field_schema.is_required,
            "help_text": field_schema.custom_rules,
        }

        if field_schema.field_type == FieldSchema.FieldType.TEXT:
            return forms.CharField(
                **common_options,
                min_length=field_schema.min_length,
                max_length=field_schema.max_length,
                widget=self._text_widget(field_schema),
            )

        if field_schema.field_type == FieldSchema.FieldType.NUMBER:
            return forms.IntegerField(
                **common_options,
                widget=forms.NumberInput(attrs={"class": "form-control"}),
            )

        if field_schema.field_type == FieldSchema.FieldType.EMAIL:
            return forms.EmailField(
                **common_options,
                min_length=field_schema.min_length,
                max_length=field_schema.max_length,
                widget=self._email_widget(field_schema),
            )

        if field_schema.field_type == FieldSchema.FieldType.DATE:
            return forms.DateField(
                **common_options,
                widget=forms.DateInput(
                    attrs={
                        "type": "date",
                        "class": "form-control",
                    }
                ),
            )

        if field_schema.field_type == FieldSchema.FieldType.SELECT:
            return forms.ChoiceField(
                **common_options,
                choices=self.SELECT_CHOICES,
                widget=forms.Select(attrs={"class": "form-control"}),
            )

        return forms.CharField(
            **common_options,
            widget=self._text_widget(field_schema),
        )


class TestRunSessionCreateForm(forms.ModelForm):
    """Form for creating a test run session from selected test cases."""

    selected_test_cases = forms.ModelMultipleChoiceField(
        queryset=TestCase.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Тест-кейсы",
        required=True,
        error_messages={
            "required": "Выберите хотя бы один тест-кейс.",
        },
    )

    class Meta:
        model = TestRunSession
        fields = ("title", "selected_test_cases")
        labels = {
            "title": "Название тест-рана",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: Регрессия формы регистрации",
                }
            ),
        }

    def __init__(self, page_schema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_schema = page_schema
        self.fields["selected_test_cases"].queryset = page_schema.test_cases.order_by(
            "priority",
            "-created_at",
            "id",
        )


class TestRunResultForm(forms.ModelForm):
    """Form for updating a test run result."""

    STATUS_CHOICES = (
        (TestRunResult.Status.NOT_RUN, "Не выполнен"),
        (TestRunResult.Status.PASSED, "Пройден"),
        (TestRunResult.Status.FAILED, "Провален"),
        (TestRunResult.Status.SKIPPED, "Пропущен"),
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label="Статус",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = TestRunResult
        fields = ("status", "notes")
        labels = {
            "notes": "Заметки",
        }
        widgets = {
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }
