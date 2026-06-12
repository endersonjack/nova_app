"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve

from dashboard import views as dashboard_views
from usuarios.forms import LoginForm
from usuarios import views as usuarios_views


def favicon_view(_request):
    return HttpResponse(status=204)


urlpatterns = [
    path('favicon.ico', favicon_view),
    path('manifest.webmanifest', dashboard_views.pwa_manifest, name='pwa_manifest'),
    path('service-worker.js', dashboard_views.pwa_service_worker, name='pwa_service_worker'),
    path('admin/', admin.site.urls),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='usuarios/login.html',
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path('', include('dashboard.urls')),
    path('meu-perfil/', usuarios_views.meu_perfil, name='meu_perfil'),
    path('meu-perfil/secao/<slug:slug>/', usuarios_views.meu_perfil_secao, name='meu_perfil_secao'),
    path('meu-perfil/cadastro/', usuarios_views.meu_perfil_editar_cadastro, name='meu_perfil_editar_cadastro'),
    path('meu-perfil/acesso/', usuarios_views.meu_perfil_editar_acesso, name='meu_perfil_editar_acesso'),
    path('usuarios/', include('usuarios.urls')),
    path('membros/', include('membros.urls')),
    path('tesouraria/', include('tesouraria.urls', namespace='tesouraria')),
    path('visitantes/', include('visitantes.urls', namespace='visitantes')),
    path('auditoria/', include('auditoria.urls', namespace='auditoria')),
]

# `static()` do Django só registra URLs quando DEBUG=True; em produção retorna [].
if getattr(settings, 'SERVE_MEDIA', settings.DEBUG):
    _mu = settings.MEDIA_URL.lstrip('/')
    if _mu and not _mu.endswith('/'):
        _mu = f'{_mu}/'
    urlpatterns += [
        re_path(
            r'^%s(?P<path>.*)$' % re.escape(_mu),
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
