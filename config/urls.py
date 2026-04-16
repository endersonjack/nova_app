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
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


def favicon_view(_request):
    return HttpResponse(status=204)


urlpatterns = [
    path('favicon.ico', favicon_view),
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('membros/', include('membros.urls')),
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
