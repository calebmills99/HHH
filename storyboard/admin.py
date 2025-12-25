from django.contrib import admin
from .models import Storyboard, StoryboardPanel


class StoryboardPanelInline(admin.TabularInline):
    model = StoryboardPanel
    extra = 0
    fields = ['panel_number', 'description', 'notes']


@admin.register(Storyboard)
class StoryboardAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description']
    inlines = [StoryboardPanelInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StoryboardPanel)
class StoryboardPanelAdmin(admin.ModelAdmin):
    list_display = ['storyboard', 'panel_number', 'description']
    list_filter = ['storyboard']
    search_fields = ['description', 'notes']
