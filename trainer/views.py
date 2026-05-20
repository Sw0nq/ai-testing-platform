"""Views for the trainer app."""
from collections import OrderedDict
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import DynamicSandboxForm, FieldSchemaForm, PageSchemaForm
from .models import FieldSchema, PageSchema
from .services import TestCaseGenerationError, generate_and_save_test_cases


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
        messages.success(self.request, "Page schema created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("trainer:page_detail", kwargs={"pk": self.object.pk})


class PageSchemaDetailView(LoginRequiredMixin, DetailView):
    model = PageSchema
    template_name = "trainer/page_detail.html"
    context_object_name = "page"


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
        messages.success(self.request, "Page schema deleted successfully.")
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
            messages.error(
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
