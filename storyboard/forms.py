from django import forms
from .models import Storyboard


class StoryboardForm(forms.ModelForm):
    """Form for creating a storyboard from text description."""
    
    class Meta:
        model = Storyboard
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a title for your storyboard'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Describe the scene you want to storyboard. Be as detailed as possible...'
            }),
        }
