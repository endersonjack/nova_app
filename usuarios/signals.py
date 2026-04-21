from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=get_user_model())
def ensure_user_profile(sender, instance, **kwargs):
    """
    Garante um UserProfile após o utilizador existir.

    Usa `transaction.on_commit` para não correr antes do Admin gravar o inline
    de UserProfile no mesmo pedido — caso contrário o sinal criava o perfil e
    o inline tentava outro INSERT na mesma `user_id` (IntegrityError).
    """
    if kwargs.get('raw'):
        return

    def criar_se_faltar():
        UserProfile.objects.get_or_create(user=instance)

    transaction.on_commit(criar_se_faltar)
