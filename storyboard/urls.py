from django.urls import path
from . import views

app_name = 'storyboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('storyboards/', views.StoryboardListView.as_view(), name='list'),
    path('storyboards/create/', views.StoryboardCreateView.as_view(), name='create'),
    path('storyboards/<int:pk>/', views.StoryboardDetailView.as_view(), name='detail'),
]
