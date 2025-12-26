from django.db import models
from django.utils import timezone


class Storyboard(models.Model):
    """Model representing a complete storyboard for a scene."""
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Original text description of the scene")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class StoryboardPanel(models.Model):
    """Model representing a single panel in a storyboard."""
    storyboard = models.ForeignKey(
        Storyboard, 
        on_delete=models.CASCADE,
        related_name='panels'
    )
    panel_number = models.IntegerField()
    description = models.TextField(help_text="Description of this panel")
    image = models.ImageField(upload_to='storyboard_panels/', blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Additional notes or direction for this panel")
    image_prompt = models.TextField(blank=True, help_text="Prompt that will be sent to Stability AI for this panel")
    prompt_approved = models.BooleanField(default=False, help_text="Whether the prompt has been reviewed by the user")
    
    class Meta:
        ordering = ['panel_number']
        unique_together = ['storyboard', 'panel_number']
    
    def __str__(self):
        return f"{self.storyboard.title} - Panel {self.panel_number}"
