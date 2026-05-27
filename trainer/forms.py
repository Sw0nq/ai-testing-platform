"""Forms for the trainer app."""
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.validators import MaxValueValidator, MinValueValidator

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
        fields = ("name", "description", "is_public")
        labels = {
            "name": "Название страницы",
            "description": "Описание",
            "is_public": "Сделать форму публичной для практики другими пользователями",
        }
        help_texts = {
            "is_public": "Другие пользователи смогут проходить форму, но не смогут её редактировать.",
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
            "is_public": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
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
            "min_value",
            "max_value",
            "min_date",
            "max_date",
            "select_options",
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
            "min_value": "Минимальное значение",
            "max_value": "Максимальное значение",
            "min_date": "Минимальная дата",
            "max_date": "Максимальная дата",
            "select_options": "Варианты выбора",
            "custom_rules": "Дополнительные правила",
            "order": "Порядок",
        }
        help_texts = {
            "min_length": "Используется только для текстовых и email-полей.",
            "max_length": "Используется только для текстовых и email-полей.",
            "min_value": "Используется только для числовых полей.",
            "max_value": "Используется только для числовых полей.",
            "min_date": "Используется только для полей даты.",
            "max_date": "Используется только для полей даты.",
            "select_options": "Для выпадающего списка укажите каждый вариант с новой строки.",
            "custom_rules": "Дополнительные подсказки или правила для тестирования.",
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
            "min_value": forms.NumberInput(attrs={"class": "form-control"}),
            "max_value": forms.NumberInput(attrs={"class": "form-control"}),
            "min_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "max_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "select_options": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Первый вариант\nВторой вариант",
                }
            ),
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
        min_value = cleaned_data.get("min_value")
        max_value = cleaned_data.get("max_value")
        min_date = cleaned_data.get("min_date")
        max_date = cleaned_data.get("max_date")
        select_options = cleaned_data.get("select_options", "")

        def ignore_fields(*field_names):
            for field_name in field_names:
                cleaned_data[field_name] = "" if field_name == "select_options" else None
                self._errors.pop(field_name, None)

        if field_type in {FieldSchema.FieldType.TEXT, FieldSchema.FieldType.EMAIL}:
            if (
                min_length is not None
                and max_length is not None
                and min_length > max_length
            ):
                raise forms.ValidationError(
                    "Минимальная длина не может быть больше максимальной."
                )
            ignore_fields(
                "min_value",
                "max_value",
                "min_date",
                "max_date",
                "select_options",
            )

        elif field_type == FieldSchema.FieldType.NUMBER:
            if min_value is not None and max_value is not None and min_value > max_value:
                raise forms.ValidationError(
                    "Минимальное значение не может быть больше максимального."
                )
            ignore_fields(
                "min_length",
                "max_length",
                "min_date",
                "max_date",
                "select_options",
            )

        elif field_type == FieldSchema.FieldType.DATE:
            if min_date is not None and max_date is not None and min_date > max_date:
                raise forms.ValidationError(
                    "Минимальная дата не может быть позже максимальной."
                )
            ignore_fields(
                "min_length",
                "max_length",
                "min_value",
                "max_value",
                "select_options",
            )

        elif field_type == FieldSchema.FieldType.SELECT:
            options = [
                option.strip()
                for option in select_options.splitlines()
                if option.strip()
            ]
            if len(options) < 2:
                raise forms.ValidationError(
                    "Для выпадающего списка нужно указать минимум два варианта."
                )
            cleaned_data["select_options"] = "\n".join(options)
            ignore_fields(
                "min_length",
                "max_length",
                "min_value",
                "max_value",
                "min_date",
                "max_date",
            )

        return cleaned_data


class DynamicSandboxForm(forms.Form):
    """Runtime form generated from FieldSchema objects for a PageSchema."""

    def __init__(self, page_schema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_schema = page_schema
        self._defects_by_field = self._build_defects_by_field()

        for field_schema in page_schema.fields.order_by("order", "id"):
            self.fields[field_schema.name] = self._build_field(field_schema)

    def _build_defects_by_field(self):
        if not self.page_schema.bug_mode_enabled:
            return {}

        profile = self.page_schema.bug_profile or {}
        defects_by_field = {}
        for defect in profile.get("defects", []):
            field_name = defect.get("field")
            defect_type = defect.get("type")
            if field_name and defect_type:
                defects_by_field.setdefault(field_name, set()).add(defect_type)
        return defects_by_field

    def _defects_for_field(self, field_schema):
        return self._defects_by_field.get(field_schema.name, set())

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
        defects = self._defects_for_field(field_schema)
        common_options = {
            "label": field_schema.label,
            "required": field_schema.is_required and "ignore_required" not in defects,
            "help_text": field_schema.custom_rules,
        }

        if field_schema.field_type == FieldSchema.FieldType.TEXT:
            return forms.CharField(
                **common_options,
                min_length=(
                    None
                    if "ignore_min_length" in defects
                    else field_schema.min_length
                ),
                max_length=(
                    None
                    if "ignore_max_length" in defects
                    else field_schema.max_length
                ),
                widget=self._text_widget(field_schema),
            )

        if field_schema.field_type == FieldSchema.FieldType.NUMBER:
            return forms.IntegerField(
                **common_options,
                min_value=(
                    None
                    if "ignore_number_min" in defects
                    else field_schema.min_value
                ),
                max_value=(
                    None
                    if "ignore_number_max" in defects
                    else field_schema.max_value
                ),
                widget=forms.NumberInput(attrs={"class": "form-control"}),
            )

        if field_schema.field_type == FieldSchema.FieldType.EMAIL:
            field_class = (
                forms.CharField
                if "ignore_email_format" in defects
                else forms.EmailField
            )
            return field_class(
                **common_options,
                min_length=(
                    None
                    if "ignore_min_length" in defects
                    else field_schema.min_length
                ),
                max_length=(
                    None
                    if "ignore_max_length" in defects
                    else field_schema.max_length
                ),
                widget=self._email_widget(field_schema),
            )

        if field_schema.field_type == FieldSchema.FieldType.DATE:
            validators = []
            attrs = {
                "type": "date",
                "class": "form-control",
            }
            if field_schema.min_date:
                if "ignore_date_min" not in defects:
                    validators.append(MinValueValidator(field_schema.min_date))
                attrs["min"] = field_schema.min_date.isoformat()
            if field_schema.max_date:
                if "ignore_date_max" not in defects:
                    validators.append(MaxValueValidator(field_schema.max_date))
                attrs["max"] = field_schema.max_date.isoformat()
            return forms.DateField(
                **common_options,
                validators=validators,
                widget=forms.DateInput(attrs=attrs),
            )

        if field_schema.field_type == FieldSchema.FieldType.SELECT:
            choices = [(option, option) for option in field_schema.select_options_list()]
            if not field_schema.is_required:
                choices = [("", "---------")] + choices
            if "ignore_select_options" in defects:
                return forms.CharField(
                    **common_options,
                    widget=forms.Select(
                        attrs={"class": "form-control"},
                        choices=choices,
                    ),
                )
            return forms.ChoiceField(
                **common_options,
                choices=choices,
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
