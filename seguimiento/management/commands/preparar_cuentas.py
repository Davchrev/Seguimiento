from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from seguimiento.models import Responsable


class Command(BaseCommand):
    help = 'Crea las tres cuentas sin contraseña inicial y las vincula a sus responsables.'

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        for code in ['ROMINA', 'DANNESY', 'ROSAURA']:
            owner, _ = Responsable.objects.get_or_create(codigo=code)
            if owner.usuario_id:
                self.stdout.write(f'{code}: ya vinculada a {owner.usuario.username}.')
                continue
            username = code.lower()
            if User.objects.filter(username=username).exists():
                raise CommandError(f'La cuenta {username} ya existe: vincúlala manualmente en /admin/.')
            user = User.objects.create_user(username=username, first_name=code.title(), password=None)
            owner.usuario = user
            owner.save(update_fields=['usuario'])
            self.stdout.write(f'{code}: cuenta {username} creada sin contraseña. Configúrala desde /admin/ o changepassword.')
