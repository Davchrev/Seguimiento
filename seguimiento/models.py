import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Responsable(models.Model):
    codigo = models.CharField('responsable', max_length=20, primary_key=True)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        db_table = 'responsables'
        ordering = ['codigo']
        constraints = [models.CheckConstraint(condition=Q(codigo__in=['ROMINA', 'DANNESY', 'ROSAURA']), name='responsable_conocido')]

    def __str__(self):
        return self.codigo.title()


class Mantenimiento(models.Model):
    atm_numero = models.CharField('número de ATM', max_length=40)
    responsable = models.ForeignKey(Responsable, db_column='responsable', on_delete=models.PROTECT)
    periodo = models.DateField('mes (primer día)', help_text='Usa el primer día del mes, por ejemplo 2026-09-01.')
    cierre = models.DateTimeField('fecha y hora de cierre', null=True, blank=True)
    observacion_cierre = models.TextField(blank=True, default='', db_default='')
    cerrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='cierres')

    class Meta:
        db_table = 'mantenimientos'
        ordering = ['atm_numero']
        constraints = [
            models.UniqueConstraint(fields=['atm_numero', 'periodo'], name='un_atm_por_mes'),
            models.CheckConstraint(condition=~Q(atm_numero=''), name='atm_no_vacio'),
        ]
        indexes = [models.Index(fields=['responsable', 'periodo'])]

    def clean(self):
        self.atm_numero = self.atm_numero.strip()
        if not self.atm_numero:
            raise ValidationError({'atm_numero': 'Ingresa el número de ATM.'})
        if self.periodo and self.periodo.day != 1:
            raise ValidationError({'periodo': 'El período debe ser el primer día del mes.'})

    def __str__(self):
        return f'ATM {self.atm_numero} · {self.periodo:%m/%Y}'


class Atencion(models.Model):
    mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.PROTECT, related_name='atenciones')
    fecha_hora = models.DateTimeField('fecha y hora de atención')
    observacion = models.TextField('observación', max_length=3000)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    registrado_el = models.DateTimeField(auto_now_add=True)
    solicitud = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        db_table = 'atenciones'
        ordering = ['fecha_hora', 'id']
        verbose_name = 'atención'
        verbose_name_plural = 'atenciones'
