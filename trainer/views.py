"""Views for the trainer app."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import PageSchemaForm
from .models import PageSchema


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

    def form_valid(self, form):
        messages.success(self.request, "Page schema updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("trainer:page_detail", kwargs={"pk": self.object.pk})


class PageSchemaDeleteView(LoginRequiredMixin, DeleteView):
    model = PageSchema
    template_name = "trainer/page_delete.html"
    context_object_name = "page"
    success_url = reverse_lazy("trainer:page_list")

    def form_valid(self, form):
        messages.success(self.request, "Page schema deleted successfully.")
        return super().form_valid(form)
