from django.db import migrations


def seed_responsables(apps, schema_editor):
    model = apps.get_model('seguimiento', 'Responsable')
    for name in ['ROMINA', 'DANNESY', 'ROSAURA']:
        model.objects.get_or_create(codigo=name)


VALIDATION = """
    SELECT CASE WHEN NEW.atm_numero != trim(NEW.atm_numero)
        OR length(NEW.atm_numero) NOT BETWEEN 1 AND 40
        THEN RAISE(ABORT, 'ATM vacio, demasiado largo o con espacios externos') END;
    SELECT CASE WHEN length(NEW.periodo) != 10
        OR NEW.periodo NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-01'
        OR substr(NEW.periodo, 1, 4) < '0001'
        OR substr(NEW.periodo, 6, 2) NOT BETWEEN '01' AND '12'
        THEN RAISE(ABORT, 'Periodo invalido: usar YYYY-MM-01') END;
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM responsables WHERE codigo = NEW.responsable)
        THEN RAISE(ABORT, 'Responsable invalido: ROMINA, DANNESY o ROSAURA') END;
"""


class Migration(migrations.Migration):
    dependencies = [('seguimiento', '0001_initial')]
    operations = [
        migrations.RunPython(seed_responsables, migrations.RunPython.noop),
        migrations.RunSQL(
            'CREATE TRIGGER etl_validate_insert BEFORE INSERT ON mantenimientos BEGIN ' + VALIDATION + ' END;',
            'DROP TRIGGER IF EXISTS etl_validate_insert;'),
        migrations.RunSQL(
            'CREATE TRIGGER etl_validate_update BEFORE UPDATE ON mantenimientos BEGIN ' + VALIDATION + ' END;',
            'DROP TRIGGER IF EXISTS etl_validate_update;'),
        migrations.RunSQL("""
            CREATE TRIGGER mantenimiento_identity BEFORE UPDATE ON mantenimientos
            WHEN OLD.atm_numero != NEW.atm_numero OR OLD.periodo != NEW.periodo
            BEGIN SELECT RAISE(ABORT, 'ATM y periodo son inmutables: crear otro mantenimiento'); END;
        """, 'DROP TRIGGER IF EXISTS mantenimiento_identity;'),
    ]
