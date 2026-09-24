from django.contrib import admin
from .models import Atencion, Mantenimiento, Responsable

admin.site.site_header = 'ATM · Administración'
admin.site.site_title = 'Seguimiento ATM'
admin.site.index_title = 'Cuentas y asignaciones'


@admin.register(Responsable)
class ResponsableAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'usuario']
    fields = ['codigo', 'usuario']

    def get_readonly_fields(self, request, obj=None):
        return ['codigo'] if obj else []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ['atm_numero', 'responsable', 'periodo', 'cierre']
    list_filter = ['periodo', 'responsable']
    search_fields = ['atm_numero']
    readonly_fields = ['cierre', 'observacion_cierre', 'cerrado_por']

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + (['atm_numero', 'periodo'] if obj else [])

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ['mantenimiento', 'fecha_hora', 'registrado_por']
    readonly_fields = ['mantenimiento', 'fecha_hora', 'observacion', 'registrado_por', 'registrado_el', 'solicitud']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
