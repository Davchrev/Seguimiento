import uuid
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import RegistroForm
from .models import Atencion, Mantenimiento


def visibles(user):
    qs = Mantenimiento.objects.select_related('responsable', 'cerrado_por')
    return qs if user.is_superuser else qs.filter(responsable__usuario=user)


@login_required
@require_http_methods(['GET'])
def dashboard(request):
    raw_month = request.GET.get('mes', timezone.localdate().strftime('%Y-%m'))
    try:
        month = datetime.strptime(raw_month, '%Y-%m').date().replace(day=1)
    except (ValueError, TypeError):
        month = timezone.localdate().replace(day=1)
        messages.error(request, 'El mes indicado no es válido.')
    base = visibles(request.user).filter(periodo=month).annotate(total_atenciones=Count('atenciones'))
    total = base.count()
    closed = base.filter(cierre__isnull=False).count()
    active = base.filter(cierre__isnull=True, total_atenciones__gt=0).count()
    state = request.GET.get('estado', '')
    qs = base
    if state == 'pendiente':
        qs = qs.filter(cierre__isnull=True, total_atenciones=0)
    elif state == 'curso':
        qs = qs.filter(cierre__isnull=True, total_atenciones__gt=0)
    elif state == 'cerrado':
        qs = qs.filter(cierre__isnull=False)
    search = request.GET.get('q', '').strip()[:40]
    if search:
        qs = qs.filter(atm_numero__icontains=search)
    return render(request, 'seguimiento/dashboard.html', {
        'items': qs, 'month': month, 'search': search, 'state': state,
        'total': total, 'closed': closed, 'active': active, 'pending': total - closed - active,
        'progress': round(closed * 100 / total) if total else 0,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    # IMMEDIATE acquires SQLite's write lock before checking ownership/state.
    # Another request or ETL reassignment cannot change either during the write.
    with transaction.atomic():
        item = get_object_or_404(visibles(request.user), pk=pk)
        action = request.POST.get('accion') if request.method == 'POST' else None
        initial = {'fecha_hora': timezone.localtime().replace(second=0, microsecond=0), 'solicitud': uuid.uuid4()}
        attention_form = RegistroForm(request.POST if action == 'atencion' else None, mantenimiento=item, initial=initial, prefix='atencion')
        close_form = RegistroForm(request.POST if action == 'cierre' else None, mantenimiento=item, cierre=True, initial=initial, prefix='cierre')
        if request.method == 'POST':
            if item.cierre:
                messages.error(request, 'Este mantenimiento ya está cerrado. No admite nuevas atenciones.')
                return redirect('detail', pk=pk)
            if action not in ['atencion', 'cierre']:
                messages.error(request, 'Acción no válida.')
            else:
                form = attention_form if action == 'atencion' else close_form
                if form.is_valid():
                    data = form.cleaned_data
                    if action == 'atencion':
                        existing = Atencion.objects.filter(solicitud=data['solicitud']).first()
                        if existing:
                            messages.info(request, 'La solicitud ya fue procesada. No se duplicó la atención.')
                        else:
                            Atencion.objects.create(mantenimiento=item, fecha_hora=data['fecha_hora'],
                                observacion=data['observacion'], registrado_por=request.user, solicitud=data['solicitud'])
                            messages.success(request, 'Atención registrada.')
                    else:
                        item.cierre = data['fecha_hora']
                        item.observacion_cierre = data['observacion']
                        item.cerrado_por = request.user
                        item.save(update_fields=['cierre', 'observacion_cierre', 'cerrado_por'])
                        messages.success(request, 'Mantenimiento preventivo cerrado.')
                    return redirect('detail', pk=pk)
        events = list(item.atenciones.select_related('registrado_por'))
    return render(request, 'seguimiento/detail.html', {'item': item, 'events': events,
        'attention_form': attention_form, 'close_form': close_form})
