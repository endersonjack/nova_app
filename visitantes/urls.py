from django.urls import path

from . import views

app_name = 'visitantes'

urlpatterns = [
    path('', views.index, name='index'),
    path('lista/', views.lista_partial, name='lista_partial'),
    path('modal/novo/', views.modal_create, name='modal_create'),
    path('criar/', views.visitante_create, name='create'),
    path('<int:pk>/', views.visitante_detalhe, name='detalhe'),
    path('<int:pk>/modal/editar/', views.modal_edit, name='modal_edit'),
    path('<int:pk>/salvar/', views.visitante_update, name='update'),
    path('<int:pk>/modal/excluir/', views.modal_delete_confirm, name='modal_delete_confirm'),
    path('<int:pk>/excluir/', views.visitante_delete, name='delete'),
]
