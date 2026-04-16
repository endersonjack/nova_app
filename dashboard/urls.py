from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='dashboard_index'),
    path('dados/', views.inicio_conteudo, name='dashboard_inicio_conteudo'),
]
