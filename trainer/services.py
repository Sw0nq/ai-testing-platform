"""Service functions for AI-assisted test case generation."""
import json
import os
import random
import re
import uuid

from django.db import transaction
from google import genai

from .models import FieldSchema, TestCase


class TestCaseGenerationError(Exception):
    """Raised when AI test case generation cannot be completed."""


BUG_DESCRIPTIONS = {
    "ignore_required": "Форма принимает пустое обязательное поле",
    "ignore_min_length": "Форма принимает значение короче минимальной длины",
    "ignore_max_length": "Форма принимает значение длиннее максимальной длины",
    "ignore_email_format": "Форма принимает некорректный email",
    "ignore_number_min": "Форма принимает число меньше минимального значения",
    "ignore_number_max": "Форма принимает число больше максимального значения",
    "ignore_date_min": "Форма принимает дату раньше минимальной",
    "ignore_date_max": "Форма принимает дату позже максимальной",
    "ignore_select_options": "Форма принимает значение вне списка вариантов",
}


def _bug_candidates_for_field(field):
    candidates = []

    if field.is_required:
        candidates.append("ignore_required")

    if field.field_type in {FieldSchema.FieldType.TEXT, FieldSchema.FieldType.EMAIL}:
        if field.min_length is not None:
            candidates.append("ignore_min_length")
        if field.max_length is not None:
            candidates.append("ignore_max_length")
        if field.field_type == FieldSchema.FieldType.EMAIL:
            candidates.append("ignore_email_format")
    elif field.field_type == FieldSchema.FieldType.NUMBER:
        if field.min_value is not None:
            candidates.append("ignore_number_min")
        if field.max_value is not None:
            candidates.append("ignore_number_max")
    elif field.field_type == FieldSchema.FieldType.DATE:
        if field.min_date is not None:
            candidates.append("ignore_date_min")
        if field.max_date is not None:
            candidates.append("ignore_date_max")
    elif field.field_type == FieldSchema.FieldType.SELECT:
        if field.select_options_list():
            candidates.append("ignore_select_options")

    return candidates


def generate_bug_profile(page_schema):
    """Generate and save a random training bug profile for a page schema."""
    candidates_by_field = []

    for field in page_schema.fields.order_by("order", "id"):
        field_candidates = [
            {
                "field": field.name,
                "type": defect_type,
                "description": BUG_DESCRIPTIONS[defect_type],
            }
            for defect_type in _bug_candidates_for_field(field)
        ]
        if field_candidates:
            candidates_by_field.append(
                {
                    "field": field.name,
                    "candidates": field_candidates,
                }
            )

    if not candidates_by_field:
        profile = {"defects": []}
    else:
        compatible_fields_count = len(candidates_by_field)
        target_count = min(3, compatible_fields_count)
        selected_defects = []
        selected_pairs = set()

        random.shuffle(candidates_by_field)

        for field_group in candidates_by_field:
            if len(selected_defects) >= target_count:
                break
            defect = random.choice(field_group["candidates"])
            selected_defects.append(defect)
            selected_pairs.add((defect["field"], defect["type"]))

        if len(selected_defects) < target_count:
            remaining_candidates = []
            for field_group in candidates_by_field:
                for defect in field_group["candidates"]:
                    pair = (defect["field"], defect["type"])
                    if pair not in selected_pairs:
                        remaining_candidates.append(defect)

            random.shuffle(remaining_candidates)
            for defect in remaining_candidates:
                if len(selected_defects) >= target_count:
                    break
                selected_defects.append(defect)
                selected_pairs.add((defect["field"], defect["type"]))

        profile = {"defects": selected_defects}

    page_schema.bug_profile = profile
    page_schema.save(update_fields=["bug_profile"])
    return profile


def clear_bug_profile(page_schema):
    """Clear generated training defects from a page schema."""
    page_schema.bug_profile = {}
    page_schema.save(update_fields=["bug_profile"])


def build_test_case_prompt(page_schema):
    """Build a Russian prompt for generating test cases for a page schema."""
    field_lines = []

    for field in page_schema.fields.order_by("order", "id"):
        rules = field.custom_rules or "нет"
        required = "да" if field.is_required else "нет"
        lines = [
            f"- Имя: {field.name}",
            f"  Метка: {field.label}",
            f"  Тип: {field.field_type}",
            f"  Обязательное: {required}",
        ]

        if field.field_type in {"text", "email"}:
            min_length = (
                field.min_length if field.min_length is not None else "не указано"
            )
            max_length = (
                field.max_length if field.max_length is not None else "не указано"
            )
            lines.extend(
                [
                    f"  Минимальная длина: {min_length}",
                    f"  Максимальная длина: {max_length}",
                ]
            )
        elif field.field_type == "number":
            min_value = (
                field.min_value if field.min_value is not None else "не указано"
            )
            max_value = (
                field.max_value if field.max_value is not None else "не указано"
            )
            lines.extend(
                [
                    f"  Минимальное значение: {min_value}",
                    f"  Максимальное значение: {max_value}",
                ]
            )
        elif field.field_type == "date":
            min_date = field.min_date.isoformat() if field.min_date else "не указано"
            max_date = field.max_date.isoformat() if field.max_date else "не указано"
            lines.extend(
                [
                    f"  Минимальная дата: {min_date}",
                    f"  Максимальная дата: {max_date}",
                ]
            )
        elif field.field_type == "select":
            options = field.select_options_list()
            options_text = ", ".join(options) if options else "не указано"
            lines.append(f"  Разрешенные варианты выбора: {options_text}")

        lines.append(f"  Правила: {rules}")
        field_lines.append("\n".join(lines))

    description = page_schema.description or "Описание не указано."
    fields_text = "\n".join(field_lines)

    return f"""
Ты QA-инженер. Сгенерируй набор тест-кейсов для ручного тестирования веб-формы.

Страница:
Название: {page_schema.name}
Описание: {description}

Поля формы:
{fields_text}

Сгенерируй ровно 10 тест-кейсов:
- 3 позитивных тест-кейса с "test_type": "positive"
- 4 негативных тест-кейса с "test_type": "negative"
- 3 граничных тест-кейса с "test_type": "boundary"
Для select-полей в позитивных тест-кейсах используй только разрешенные варианты выбора.
В негативных тест-кейсах можно использовать несуществующее значение select-поля для проверки валидации.
Верни только строго валидный JSON.
Не добавляй markdown.
Не добавляй пояснения.
Не добавляй комментарии.
JSON должен точно соответствовать формату:
{{
  "test_cases": [
    {{
      "title": "...",
      "input_data": {{
        "field_name": "value"
      }},
      "expected_result": "...",
      "test_type": "positive|negative|boundary",
      "priority": "high|medium|low"
    }}
  ]
}}
""".strip()


def call_gemini(prompt):
    """Call Gemini API and return generated text."""
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    if not api_key:
        raise TestCaseGenerationError(
            "Не задан GEMINI_API_KEY. Укажите ключ Gemini API в переменных окружения."
        )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except Exception as exc:
        raise TestCaseGenerationError(f"Ошибка запроса к Gemini API: {exc}") from exc

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise TestCaseGenerationError("Gemini вернул пустой ответ.")

    return text


def parse_test_cases_json(raw_text):
    """Parse AI output as JSON and return a list of test case dictionaries."""
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    if not text.startswith("{"):
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = raw_text.strip().replace("\n", " ")[:300]
        raise TestCaseGenerationError(
            f"Ответ AI не является валидным JSON. Фрагмент ответа: {snippet}"
        ) from exc

    test_cases = data.get("test_cases")
    if not isinstance(test_cases, list):
        raise TestCaseGenerationError('Ответ AI должен содержать список "test_cases".')

    return test_cases


def generate_and_save_test_cases(page_schema):
    """Generate test cases with AI and save them to the database."""
    prompt = build_test_case_prompt(page_schema)
    raw_text = call_gemini(prompt)
    parsed_test_cases = parse_test_cases_json(raw_text)
    generation_batch = uuid.uuid4()
    created_test_cases = []

    allowed_test_types = {choice[0] for choice in TestCase.TestType.choices}
    allowed_priorities = {choice[0] for choice in TestCase.Priority.choices}

    with transaction.atomic():
        for item in parsed_test_cases:
            if not isinstance(item, dict):
                continue

            test_type = item.get("test_type")
            if test_type not in allowed_test_types:
                test_type = TestCase.TestType.POSITIVE

            priority = item.get("priority")
            if priority not in allowed_priorities:
                priority = TestCase.Priority.MEDIUM

            input_data = item.get("input_data")
            if not isinstance(input_data, dict):
                input_data = {}

            test_case = TestCase.objects.create(
                page=page_schema,
                generation_batch=generation_batch,
                title=item.get("title") or "Сгенерированный тест-кейс",
                input_data=input_data,
                expected_result=item.get("expected_result") or "",
                test_type=test_type,
                priority=priority,
            )
            created_test_cases.append(test_case)

    return created_test_cases, generation_batch
