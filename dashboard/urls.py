from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='dashboard_index'),
    path(
        'privacidade/',
        views.politica_privacidade,
        name='politica_privacidade',
    ),
    path('dados/', views.inicio_conteudo, name='dashboard_inicio_conteudo'),
    path('ministerios/', views.ministerios_index, name='dashboard_ministerios'),
    path('seminario/', views.seminario_index, name='dashboard_seminario'),
    path('estatistica/', views.estatistica_index, name='dashboard_estatistica'),
    path(
        'estatistica/dados/',
        views.estatistica_conteudo,
        name='dashboard_estatistica_conteudo',
    ),
]
