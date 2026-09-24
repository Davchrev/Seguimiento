from django import forms
from django.utils import timezone


class RegistroForm(forms.Form):
    fecha_hora = forms.DateTimeField(
        label='Fecha y hora', input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}))
    observacion = forms.CharField(label='Observación', max_length=3000,
                                 widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe el trabajo realizado…'}))
    solicitud = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, mantenimiento, cierre=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.mantenimiento = mantenimiento
        self.es_cierre = cierre
        self.fields['observacion'].required = not cierre
        if cierre:
            self.fields['observacion'].label = 'Observación final (opcional)'

    def clean_fecha_hora(self):
        value = self.cleaned_data['fecha_hora']
        if value > timezone.now():
            raise forms.ValidationError('La fecha y hora no pueden estar en el futuro.')
        if timezone.localtime(value).date() < self.mantenimiento.periodo:
            raise forms.ValidationError('La fecha no puede ser anterior al mes del mantenimiento.')
        if self.es_cierre:
            ultima = self.mantenimiento.atenciones.order_by('-fecha_hora').first()
            if not ultima:
                raise forms.ValidationError('Registra al menos una atención antes de cerrar.')
            if value < ultima.fecha_hora:
                raise forms.ValidationError('El cierre no puede ser anterior a la última atención.')
        return value
