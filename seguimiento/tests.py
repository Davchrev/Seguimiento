import uuid
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Atencion, Mantenimiento, Responsable


class MantenimientoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.romina = User.objects.create_user('romina', password='Only-test-password-482')
        cls.dannesy = User.objects.create_user('dannesy', password='Only-test-password-482')
        cls.rosaura = User.objects.create_user('rosaura', password='Only-test-password-482')
        cls.admin = User.objects.create_superuser('admin', password='Only-test-password-482')
        cls.unlinked = User.objects.create_user('sin_asignar', is_staff=True)
        for name, user in [('ROMINA', cls.romina), ('DANNESY', cls.dannesy), ('ROSAURA', cls.rosaura)]:
            Responsable.objects.update_or_create(codigo=name, defaults={'usuario': user})
        cls.item = Mantenimiento.objects.create(atm_numero='00123', responsable_id='ROMINA', periodo=date(2025, 1, 1))
        cls.other = Mantenimiento.objects.create(atm_numero='00456', responsable_id='DANNESY', periodo=date(2025, 1, 1))
        cls.rosa_item = Mantenimiento.objects.create(atm_numero='00789', responsable_id='ROSAURA', periodo=date(2025, 1, 1))

    def setUp(self):
        self.client.force_login(self.romina)

    def post(self, action='atencion', when='2025-01-10T09:30', observation='Limpieza y revisión.', token=None, item=None):
        return self.client.post(reverse('detail', args=[(item or self.item).pk]), {
            'accion': action, f'{action}-fecha_hora': when,
            f'{action}-observacion': observation, f'{action}-solicitud': str(token or uuid.uuid4()),
        })

    def sql_load(self, atm='00999', owner='ROSAURA', month='2025-01-01'):
        with connection.cursor() as cursor:
            cursor.execute('''INSERT INTO mantenimientos (atm_numero, responsable, periodo)
                VALUES (%s, %s, %s) ON CONFLICT(atm_numero, periodo)
                DO UPDATE SET responsable = excluded.responsable''', [atm, owner, month])

    def test_anonymous_redirected(self):
        self.client.logout()
        self.assertRedirects(self.client.get('/'), '/ingresar/?next=/')
        self.assertEqual(self.client.get(reverse('detail', args=[self.item.pk])).status_code, 302)

    def test_each_responsible_sees_only_own_cards(self):
        for user, own, hidden in [(self.romina, '00123', '00456'), (self.dannesy, '00456', '00789'), (self.rosaura, '00789', '00123')]:
            self.client.force_login(user)
            response = self.client.get('/?mes=2025-01')
            self.assertContains(response, 'ATM ' + own)
            self.assertNotContains(response, 'ATM ' + hidden)
            self.assertEqual(response.context['total'], 1)

    def test_direct_url_and_post_cannot_cross_owner(self):
        self.assertEqual(self.client.get(reverse('detail', args=[self.other.pk])).status_code, 404)
        self.assertEqual(self.post(item=self.other).status_code, 404)
        self.assertEqual(self.post(action='cierre', item=self.other).status_code, 404)
        self.assertEqual(Atencion.objects.count(), 0)

    def test_staff_without_assignment_does_not_get_global_access(self):
        self.client.force_login(self.unlinked)
        response = self.client.get('/?mes=2025-01')
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(self.client.get(reverse('detail', args=[self.item.pk])).status_code, 404)

    def test_superuser_sees_all(self):
        self.client.force_login(self.admin)
        response = self.client.get('/?mes=2025-01')
        self.assertEqual(response.context['total'], 3)
        self.assertContains(response, 'Administración')

    def test_multiple_attentions_then_closure(self):
        self.assertEqual(self.post().status_code, 302)
        self.assertEqual(self.post(when='2025-01-11T10:30', observation='Pruebas completadas.').status_code, 302)
        self.assertEqual(self.item.atenciones.count(), 2)
        first = self.item.atenciones.first()
        self.assertEqual(first.fecha_hora.hour, 14)  # 09:30 Peru = 14:30 UTC.
        response = self.post(action='cierre', when='2025-01-11T11:00', observation='')
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertIsNotNone(self.item.cierre)
        self.assertEqual(self.item.cerrado_por, self.romina)
        detail = self.client.get(reverse('detail', args=[self.item.pk]))
        self.assertContains(detail, 'Trabajo completado')
        self.assertNotContains(detail, 'Guardar atención')

    def test_same_form_retry_is_idempotent(self):
        token = uuid.uuid4()
        self.post(token=token)
        self.post(token=token)
        self.assertEqual(self.item.atenciones.count(), 1)

    def test_no_close_without_attention(self):
        response = self.post(action='cierre')
        self.assertContains(response, 'Registra al menos una atención')
        self.item.refresh_from_db()
        self.assertIsNone(self.item.cierre)

    def test_close_before_last_attention_is_rejected(self):
        self.post(when='2025-01-11T10:30')
        response = self.post(action='cierre', when='2025-01-11T10:29')
        self.assertContains(response, 'El cierre no puede ser anterior')
        self.item.refresh_from_db()
        self.assertIsNone(self.item.cierre)

    def test_after_close_no_new_attention_or_second_close(self):
        self.post()
        self.post(action='cierre', when='2025-01-10T10:00')
        self.item.refresh_from_db()
        closed = self.item.cierre
        self.post(when='2025-01-11T10:00')
        self.post(action='cierre', when='2025-01-12T10:00')
        self.assertEqual(self.item.atenciones.count(), 1)
        self.item.refresh_from_db()
        self.assertEqual(self.item.cierre, closed)

    def test_future_and_before_period_dates_rejected(self):
        future = timezone.localtime(timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.assertContains(self.post(when=future), 'no pueden estar en el futuro')
        self.assertContains(self.post(when='2024-12-31T23:59'), 'anterior al mes')
        self.assertEqual(Atencion.objects.count(), 0)

    def test_observation_required_and_html_escaped(self):
        self.assertEqual(self.post(observation='   ').status_code, 200)
        self.assertEqual(Atencion.objects.count(), 0)
        self.post(observation='<script>alert(1)</script>')
        response = self.client.get(reverse('detail', args=[self.item.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_direct_sql_load_appears_in_owner_dashboard(self):
        self.sql_load()
        self.client.force_login(self.rosaura)
        response = self.client.get('/?mes=2025-01')
        self.assertContains(response, 'ATM 00999')
        loaded = Mantenimiento.objects.get(atm_numero='00999')
        self.assertEqual(loaded.observacion_cierre, '')
        self.assertIsNone(loaded.cierre)

    def test_etl_reassignment_preserves_history_and_revokes_old_owner(self):
        self.post()
        self.post(action='cierre', when='2025-01-10T10:00')
        self.sql_load(atm='00123', owner='DANNESY')
        self.assertEqual(self.client.get(reverse('detail', args=[self.item.pk])).status_code, 404)
        self.assertEqual(self.post().status_code, 404)
        self.client.force_login(self.dannesy)
        response = self.client.get(reverse('detail', args=[self.item.pk]))
        self.assertContains(response, 'Limpieza y revisión.')
        self.assertContains(response, 'Trabajo completado')
        self.assertEqual(self.item.atenciones.count(), 1)

    def test_one_atm_each_month_and_previous_month_unchanged(self):
        self.sql_load(atm='00123', owner='ROSAURA', month='2025-02-01')
        self.assertEqual(Mantenimiento.objects.filter(atm_numero='00123').count(), 2)
        self.item.refresh_from_db()
        self.assertEqual(self.item.responsable_id, 'ROMINA')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Mantenimiento.objects.create(atm_numero='00123', responsable_id='ROMINA', periodo=date(2025, 1, 1))

    def test_sql_validation_rejects_bad_source_rows(self):
        cases = [('', 'ROMINA', '2025-01-01'), ('   ', 'ROMINA', '2025-01-01'),
                 ('123 ', 'ROMINA', '2025-01-01'), ('x' * 41, 'ROMINA', '2025-01-01'),
                 ('123', 'INVALIDA', '2025-01-01'), ('123', 'romina', '2025-01-01'),
                 ('123', 'ROMINA', '2025-01-15'), ('123', 'ROMINA', '2025-13-01'),
                 ('123', 'ROMINA', '0000-01-01'), ('123', 'ROMINA', '2025-1-01')]
        for atm, owner, month in cases:
            with self.subTest(atm=atm, owner=owner, month=month):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.sql_load(atm=atm, owner=owner, month=month)

    def test_sql_batch_rollback(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.sql_load(atm='00999')
            self.sql_load(atm='00888', owner='INVALIDA')
        self.assertFalse(Mantenimiento.objects.filter(atm_numero='00999').exists())

    def test_identity_cannot_be_changed(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Mantenimiento.objects.filter(pk=self.item.pk).update(atm_numero='OTRO')

    def test_filters_and_summary(self):
        self.post()
        response = self.client.get('/?mes=2025-01&estado=curso&q=001')
        self.assertContains(response, 'ATM 00123')
        self.assertEqual(response.context['active'], 1)
        self.assertNotContains(self.client.get('/?mes=2025-01&estado=cerrado'), 'ATM 00123')
        self.assertEqual(self.client.get('/?mes=no-valido').status_code, 200)

    def test_csrf_required_for_mutation(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.romina)
        response = csrf_client.post(reverse('detail', args=[self.item.pk]), {'accion': 'atencion'})
        self.assertEqual(response.status_code, 403)

    def test_responsible_cannot_enter_admin(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_months_can_finish_late(self):
        self.post(when='2025-02-02T10:00')
        self.post(action='cierre', when='2025-02-02T11:00')
        self.item.refresh_from_db()
        self.assertIsNotNone(self.item.cierre)
