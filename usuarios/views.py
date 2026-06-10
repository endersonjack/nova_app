from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import MeuPerfilAcessoForm, MeuPerfilMembroForm


def index(request):
    return render(request, 'usuarios/index.html')


def _style_password_form(form):
    for name, field in form.fields.items():
        field.widget.attrs.setdefault('class', 'form-control rounded-3')
        if name == 'old_password':
            field.widget.attrs.setdefault('autocomplete', 'current-password')
        else:
            field.widget.attrs.setdefault('autocomplete', 'new-password')
    return form


MEU_PERFIL_SECOES = {
    'dados-pessoais': 'membros/partials/detalhe/_secao_dados_pessoais_display.html',
    'localidade': 'membros/partials/detalhe/_secao_localidade_display.html',
    'familia': 'membros/partials/detalhe/_secao_familia_display.html',
    'batismo': 'membros/partials/detalhe/_secao_batismo_display.html',
    'informacoes': 'membros/partials/detalhe/_secao_informacoes_display.html',
    'ministerios': 'membros/partials/detalhe/_secao_ministerios_display.html',
}


def _membro_do_usuario(user):
    perfil = getattr(user, 'perfil', None)
    if not perfil or not perfil.membro_id:
        return None
    return perfil.membro


def _meu_perfil_context(membro, secao_ativa='dados-pessoais'):
    return {
        'membro': membro,
        'secao_ativa': secao_ativa,
        'secao_slug': secao_ativa,
        'meu_perfil_mode': True,
        'secao_include': MEU_PERFIL_SECOES[secao_ativa],
    }


@login_required
def meu_perfil(request):
    membro = _membro_do_usuario(request.user)
    return render(
        request,
        'usuarios/meu_perfil.html',
        _meu_perfil_context(membro) if membro else {'membro': None},
    )


@login_required
def meu_perfil_secao(request, slug):
    if slug not in MEU_PERFIL_SECOES:
        raise Http404()
    membro = _membro_do_usuario(request.user)
    if not membro:
        raise Http404()
    return render(
        request,
        MEU_PERFIL_SECOES[slug],
        _meu_perfil_context(membro, slug),
    )


@login_required
def meu_perfil_editar_cadastro(request):
    membro = _membro_do_usuario(request.user)
    if not membro:
        messages.warning(request, 'Seu usuário ainda não está vinculado a um cadastro de membro.')
        return redirect('meu_perfil')

    form = MeuPerfilMembroForm(instance=membro)
    if request.method == 'POST':
        form = MeuPerfilMembroForm(request.POST, request.FILES, instance=membro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cadastro de membro atualizado.')
            return redirect('meu_perfil')

    return render(
        request,
        'usuarios/meu_perfil_editar_cadastro.html',
        {
            'membro': membro,
            'form': form,
        },
    )


@login_required
def meu_perfil_editar_acesso(request):
    access_form = MeuPerfilAcessoForm(instance=request.user)
    password_form = _style_password_form(PasswordChangeForm(request.user))

    if request.method == 'POST':
        action = request.POST.get('form') or ''
        if action == 'acesso':
            access_form = MeuPerfilAcessoForm(request.POST, instance=request.user)
            if access_form.is_valid():
                access_form.save()
                messages.success(request, 'Dados de acesso atualizados.')
                return redirect('meu_perfil')
        elif action == 'senha':
            password_form = _style_password_form(PasswordChangeForm(request.user, request.POST))
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha alterada com sucesso.')
                return redirect('meu_perfil')

    return render(
        request,
        'usuarios/meu_perfil_editar_acesso.html',
        {
            'access_form': access_form,
            'password_form': password_form,
        },
    )
