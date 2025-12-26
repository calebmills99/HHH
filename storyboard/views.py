import os
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import Storyboard, StoryboardPanel
from .forms import StoryboardForm
from .utils import generate_storyboard_panels, generate_panel_image, build_image_prompt


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stability_api_configured'] = bool(os.environ.get('STABILITY_API_KEY'))
        return context


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


def generate_panel_image_view(request, pk):
    """Allow users to review and approve a prompt before generating an image."""
    panel = get_object_or_404(StoryboardPanel, pk=pk)
    if request.method != 'POST':
        return redirect('storyboard:detail', pk=panel.storyboard_id)

    # Normalize the prompt input; treat empty/whitespace as no prompt
    raw_prompt = request.POST.get('prompt')
    prompt = (raw_prompt or '').strip()

    if prompt:
        # User provided a non-empty prompt; store and mark as approved
        panel.image_prompt = prompt
        panel.prompt_approved = True
        update_fields = ['image_prompt', 'prompt_approved']
    else:
        # No usable prompt provided; fall back to generated prompt and leave unapproved
        panel.image_prompt = build_image_prompt(panel.description)
        panel.prompt_approved = False
        update_fields = ['image_prompt', 'prompt_approved']

    panel.save(update_fields=update_fields)

    if not os.environ.get('STABILITY_API_KEY'):
        messages.error(request, "Stability API key is missing. Add STABILITY_API_KEY to your environment and try again.")
        return redirect('storyboard:detail', pk=panel.storyboard_id)

    # Only generate image if prompt was approved
    if panel.prompt_approved and generate_panel_image(panel):
        messages.success(request, f"Image generated for panel {panel.panel_number}.")
    elif panel.prompt_approved:
        messages.error(request, f"Failed to generate image for panel {panel.panel_number}. Please check logs or try again.")

    return redirect('storyboard:detail', pk=panel.storyboard_id)
