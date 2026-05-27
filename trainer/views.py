"""Views for the trainer app."""
from collections import OrderedDict
import json

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    DynamicSandboxForm,
    FieldSchemaForm,
    LoginForm,
    PageSchemaForm,
    RegisterForm,
    TestRunResultForm,
    TestRunSessionCreateForm,
)
from .models import FieldSchema, PageSchema, TestCase, TestRunResult, TestRunSession
from .services import TestCaseGenerationError, generate_and_save_test_cases


def register_view(request):
    """Register a new user and sign them in."""
    if request.user.is_authenticated:
        return redirect("trainer:page_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Регистрация завершена. Вы вошли в систему.")
            return redirect("trainer:page_list")
        messages.warning(request, "Проверьте данные регистрации.")
    else:
        form = RegisterForm()

    return render(request, "trainer/register.html", {"form": form})


def login_view(request):
    """Authenticate a user."""
    if request.user.is_authenticated:
        return redirect("trainer:page_list")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, "Вы вошли в систему.")
            return redirect("trainer:page_list")
        messages.warning(request, "Проверьте имя пользователя и пароль.")
    else:
        form = LoginForm(request)

    return render(request, "trainer/login.html", {"form": form})


def logout_view(request):
    """Sign out the current user."""
    auth_logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect("trainer:login")


class PageSchemaListView(LoginRequiredMixin, ListView):
    model = PageSchema
    template_name = "trainer/page_list.html"
    context_object_name = "pages"


class PageSchemaCreateView(LoginRequiredMixin, CreateView):
    model = PageSchema
    form_class = PageSchemaForm
    template_name = "trainer/page_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Страница успешно создана.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("trainer:page_detail", kwargs={"pk": self.object.pk})


class PageSchemaDetailView(LoginRequiredMixin, DetailView):
    model = PageSchema
    template_name = "trainer/page_detail.html"
    context_object_name = "page"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sessions = []
        queryset = (
            self.object.test_run_sessions.select_related("user")
            .prefetch_related("results")
            .order_by("-created_at")
        )

        for session in queryset:
            results = list(session.results.all())
            total_count = len(results)
            passed_count = sum(1 for result in results if result.status == "passed")
            failed_count = sum(1 for result in results if result.status == "failed")
            skipped_count = sum(1 for result in results if result.status == "skipped")
            not_run_count = sum(1 for result in results if result.status == "not_run")
            completed_count = total_count - not_run_count
            progress = round((completed_count / total_count) * 100) if total_count else 0

            sessions.append(
                {
                    "object": session,
                    "display_title": session.title
                    or f"Тест-ран от {session.created_at:%Y-%m-%d %H:%M}",
                    "total_count": total_count,
                    "passed_count": passed_count,
                    "failed_count": failed_count,
                    "skipped_count": skipped_count,
                    "not_run_count": not_run_count,
                    "progress": progress,
                }
            )

        context["test_run_sessions"] = sessions
        return context


class PageSchemaUpdateView(LoginRequiredMixin, UpdateView):
    model = PageSchema
    form_class = PageSchemaForm
    template_name = "trainer/page_edit.html"
    context_object_name = "page"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prefix"] = "page"
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fields"] = self.object.fields.order_by("order", "id")
        context.setdefault("field_form", FieldSchemaForm(prefix="field"))
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if "add_field" in request.POST:
            page_form = PageSchemaForm(instance=self.object, prefix="page")
            field_form = FieldSchemaForm(request.POST, prefix="field")
            if field_form.is_valid():
                field = field_form.save(commit=False)
                field.page = self.object
                field.save()
                messages.success(request, "Поле успешно добавлено.")
                return redirect("trainer:page_edit", pk=self.object.pk)

            context = self.get_context_data(form=page_form, field_form=field_form)
            return self.render_to_response(context)

        if "save_page" in request.POST:
            page_form = PageSchemaForm(
                request.POST,
                instance=self.object,
                prefix="page",
            )
            if page_form.is_valid():
                self.object = page_form.save()
                messages.success(request, "Страница успешно обновлена.")
                return redirect("trainer:page_edit", pk=self.object.pk)

            context = self.get_context_data(
                form=page_form,
                field_form=FieldSchemaForm(prefix="field"),
            )
            return self.render_to_response(context)

        return redirect("trainer:page_edit", pk=self.object.pk)

    def form_valid(self, form):
        messages.success(self.request, "Страница успешно обновлена.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("trainer:page_edit", kwargs={"pk": self.object.pk})


class PageSchemaDeleteView(LoginRequiredMixin, DeleteView):
    model = PageSchema
    template_name = "trainer/page_delete.html"
    context_object_name = "page"
    success_url = reverse_lazy("trainer:page_list")

    def form_valid(self, form):
        messages.success(self.request, "Страница успешно удалена.")
        return super().form_valid(form)


def _get_test_case_groups(page):
    groups = OrderedDict()
    test_cases = page.test_cases.order_by("-created_at", "generation_batch", "title")

    for test_case in test_cases:
        batch = str(test_case.generation_batch)
        groups.setdefault(batch, []).append(test_case)

    return groups.items()


@login_required
def page_generate_test_cases(request, pk):
    page = get_object_or_404(PageSchema, pk=pk)
    fields = page.fields.order_by("order", "id")
    generated_test_cases = []
    generation_batch = None

    if request.method == "POST":
        if not fields.exists():
            messages.warning(
                request,
                "Нельзя сгенерировать тест-кейсы: сначала добавьте поля формы.",
            )
        else:
            try:
                generated_test_cases, generation_batch = generate_and_save_test_cases(page)
                messages.success(
                    request,
                    f"Сгенерировано тест-кейсов: {len(generated_test_cases)}.",
                )
            except TestCaseGenerationError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, f"Ошибка генерации тест-кейсов: {exc}")

    return render(
        request,
        "trainer/generate_test_cases.html",
        {
            "page": page,
            "fields": fields,
            "generated_test_cases": generated_test_cases,
            "generation_batch": generation_batch,
            "test_case_groups": _get_test_case_groups(page),
        },
    )


def _group_test_cases_by_priority(test_cases):
    return {
        "high": [test_case for test_case in test_cases if test_case.priority == "high"],
        "medium": [
            test_case for test_case in test_cases if test_case.priority == "medium"
        ],
        "low": [test_case for test_case in test_cases if test_case.priority == "low"],
    }


@login_required
def test_run_create_view(request, pk):
    page = get_object_or_404(PageSchema, pk=pk)
    test_cases = list(page.test_cases.order_by("priority", "-created_at", "id"))

    if request.method == "POST":
        form = TestRunSessionCreateForm(page, request.POST)
        if form.is_valid():
            selected_test_cases = form.cleaned_data["selected_test_cases"]
            with transaction.atomic():
                session = form.save(commit=False)
                session.page = page
                session.user = request.user
                session.save()
                for test_case in selected_test_cases:
                    TestRunResult.objects.create(
                        session=session,
                        test_case=test_case,
                        status=TestRunResult.Status.NOT_RUN,
                    )

            messages.success(request, "Тест-ран создан.")
            return redirect(
                "trainer:test_run_execute",
                page_id=page.pk,
                session_id=session.pk,
            )
        messages.warning(request, "Выберите хотя бы один тест-кейс.")
    else:
        form = TestRunSessionCreateForm(page)

    return render(
        request,
        "trainer/test_run_create.html",
        {
            "page": page,
            "test_cases": test_cases,
            "grouped_test_cases": _group_test_cases_by_priority(test_cases),
            "form": form,
        },
    )


def _sort_results_for_execution(results):
    priority_order = {
        TestCase.Priority.HIGH: 0,
        TestCase.Priority.MEDIUM: 1,
        TestCase.Priority.LOW: 2,
    }
    return sorted(
        results,
        key=lambda result: (
            priority_order.get(result.test_case.priority, 99),
            result.test_case_id,
        ),
    )


@login_required
def test_run_execute_view(request, page_id, session_id):
    page = get_object_or_404(PageSchema, pk=page_id)
    session = get_object_or_404(
        TestRunSession,
        pk=session_id,
        page=page,
        user=request.user,
    )
    submitted_data = None
    sandbox_form = DynamicSandboxForm(page_schema=page)

    if request.method == "POST" and "submit_sandbox" in request.POST:
        sandbox_form = DynamicSandboxForm(page_schema=page, data=request.POST)
        if sandbox_form.is_valid():
            messages.success(request, "Форма песочницы успешно отправлена.")
            submitted_data = json.dumps(
                sandbox_form.cleaned_data,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        else:
            messages.warning(request, "Проверьте данные в форме песочницы.")

    if request.method == "POST" and "save_result" in request.POST:
        result = get_object_or_404(
            TestRunResult,
            pk=request.POST.get("result_id"),
            session=session,
        )
        result_form = TestRunResultForm(request.POST, instance=result)
        if result_form.is_valid():
            result = result_form.save(commit=False)
            result.executed_at = timezone.now()
            result.save()
            messages.success(request, "Результат тест-кейса сохранен.")
            return redirect(
                "trainer:test_run_execute",
                page_id=page.pk,
                session_id=session.pk,
            )
        messages.warning(request, "Проверьте статус и заметки.")

    results = _sort_results_for_execution(
        list(session.results.select_related("test_case").all())
    )

    return render(
        request,
        "trainer/test_run_execute.html",
        {
            "page": page,
            "session": session,
            "sandbox_form": sandbox_form,
            "submitted_data": submitted_data,
            "results": results,
            "result_form": TestRunResultForm(),
        },
    )


class SandboxView(LoginRequiredMixin, View):
    template_name = "trainer/sandbox.html"

    def get_page(self):
        return get_object_or_404(PageSchema, pk=self.kwargs["pk"])

    def get(self, request, *args, **kwargs):
        page = self.get_page()
        form = DynamicSandboxForm(page_schema=page)
        return render(
            request,
            self.template_name,
            {
                "page": page,
                "form": form,
            },
        )

    def post(self, request, *args, **kwargs):
        page = self.get_page()
        form = DynamicSandboxForm(page_schema=page, data=request.POST)
        submitted_data = None

        if form.is_valid():
            messages.success(request, "Форма успешно отправлена")
            submitted_data = json.dumps(
                form.cleaned_data,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        return render(
            request,
            self.template_name,
            {
                "page": page,
                "form": form,
                "submitted_data": submitted_data,
            },
        )


class FieldSchemaUpdateView(LoginRequiredMixin, UpdateView):
    model = FieldSchema
    form_class = FieldSchemaForm
    template_name = "trainer/field_edit.html"
    context_object_name = "field"

    def dispatch(self, request, *args, **kwargs):
        self.page = get_object_or_404(PageSchema, pk=kwargs["page_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(
            FieldSchema,
            pk=self.kwargs["field_id"],
            page=self.page,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page"] = self.page
        return context

    def form_valid(self, form):
        messages.success(self.request, "Поле успешно обновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer:page_edit", kwargs={"pk": self.page.pk})


class FieldSchemaDeleteView(LoginRequiredMixin, DeleteView):
    model = FieldSchema
    template_name = "trainer/field_delete.html"
    context_object_name = "field"

    def dispatch(self, request, *args, **kwargs):
        self.page = get_object_or_404(PageSchema, pk=kwargs["page_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(
            FieldSchema,
            pk=self.kwargs["field_id"],
            page=self.page,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page"] = self.page
        return context

    def form_valid(self, form):
        messages.success(self.request, "Поле успешно удалено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trainer:page_edit", kwargs={"pk": self.page.pk})
