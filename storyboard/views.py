from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import Storyboard, StoryboardPanel
from .forms import StoryboardForm
from .utils import generate_storyboard_panels


class StoryboardListView(ListView):
    """View to list all storyboards."""
    model = Storyboard
    template_name = 'storyboard/storyboard_list.html'
    context_object_name = 'storyboards'
    paginate_by = 10


class StoryboardDetailView(DetailView):
    """View to display a single storyboard with all its panels."""
    model = Storyboard
    template_name = 'storyboard/storyboard_detail.html'
    context_object_name = 'storyboard'


class StoryboardCreateView(CreateView):
    """View to create a new storyboard from text description."""
    model = Storyboard
    form_class = StoryboardForm
    template_name = 'storyboard/storyboard_create.html'
    success_url = reverse_lazy('storyboard:list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Generate storyboard panels from the description
        generate_storyboard_panels(self.object)
        return response


def home(request):
    """Home page view."""
    return render(request, 'storyboard/home.html')
