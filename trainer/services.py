"""Service functions for AI-assisted test case generation."""
import json
import os
import re
import uuid

from django.db import transaction
from google import genai

from .models import TestCase


class TestCaseGenerationError(Exception):
    """Raised when AI test case generation cannot be completed."""


def build_test_case_prompt(page_schema):
    """Build a Russian prompt for generating test cases for a page schema."""
    field_lines = []

    for field in page_schema.fields.order_by("order", "id"):
        rules = field.custom_rules or "нет"
        min_length = field.min_length if field.min_length is not None else "не указано"
        max_length = field.max_length if field.max_length is not None else "не указано"
        required = "да" if field.is_required else "нет"
        field_lines.append(
            "\n".join(
                [
                    f"- Имя: {field.name}",
                    f"  Метка: {field.label}",
                    f"  Тип: {field.field_type}",
                    f"  Обязательное: {required}",
                    f"  Минимальная длина: {min_length}",
                    f"  Максимальная длина: {max_length}",
                    f"  Правила: {rules}",
                ]
            )
        )

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
