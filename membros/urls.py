from django.urls import path

from . import views

app_name = 'membros'

urlpatterns = [
    path('mapa/', views.mapa_membros, name='mapa'),
    path('', views.index, name='membros_index'),
    path('lista/', views.lista_partial, name='lista_partial'),
    path('buscar/', views.autocomplete, name='autocomplete'),
    path('modal/novo/', views.modal_create, name='modal_create'),
    path('modal/<int:pk>/excluir/', views.modal_delete_confirm, name='modal_delete_confirm'),
    path('criar/', views.membro_create, name='create'),
    path('<int:pk>/secao/<slug:slug>/salvar/', views.membro_secao_salvar, name='secao_salvar'),
    path('<int:pk>/secao/<slug:slug>/modal/', views.membro_secao_modal, name='secao_modal'),
    path('<int:pk>/secao/<slug:slug>/', views.membro_secao, name='secao'),
    path('<int:pk>/excluir/', views.membro_delete, name='delete'),
    path('<int:pk>/', views.membro_detalhe, name='detalhe'),
]
