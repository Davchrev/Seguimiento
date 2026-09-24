# Carga directa en SQLite

La aplicación usa `db.sqlite3` en la raíz del proyecto. Se puede cambiar con la variable `SQLITE_PATH`.
Ejecutar primero `python manage.py migrate`. Django crea las tablas; el ETL carga sus filas.

## Tabla de destino: `mantenimientos`

Cada fila es el mantenimiento mensual de un ATM. El ETL escribe únicamente estas columnas:

| Columna | Tipo | Valor |
| --- | --- | --- |
| `atm_numero` | TEXT | Identificador del ATM, de 1 a 40 caracteres, sin espacios externos. Conservar los ceros iniciales. |
| `responsable` | TEXT | `ROMINA`, `DANNESY` o `ROSAURA`, en mayúsculas. |
| `periodo` | DATE/TEXT | Primer día del mes: `2026-09-01`. |

Tu tabla de origen puede tener solo **ATM y Responsable**. El ETL añade `periodo` como parámetro de la carga mensual: no necesitas agregarlo a cada fila de origen. Siempre indicar el mes explícitamente, especialmente al cargar períodos anteriores.

`id` es autogenerado. `cierre`, `observacion_cierre` y `cerrado_por_id` los administra la app. No incluirlos en el ETL.
La restricción `(atm_numero, periodo)` impide duplicados. Los disparadores de SQLite validan ATM, período y responsable incluso en una conexión externa.

## SQL de carga

Conectar al **mismo archivo** que usa Django. Activar las claves foráneas en cada conexión y usar una transacción corta. Ejemplo ilustrativo; reemplazar por datos reales:

```sql
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 20000;
BEGIN IMMEDIATE;

INSERT INTO mantenimientos (atm_numero, responsable, periodo)
VALUES ('00123', 'ROMINA', '2026-09-01')
ON CONFLICT(atm_numero, periodo)
DO UPDATE SET responsable = excluded.responsable;

INSERT INTO mantenimientos (atm_numero, responsable, periodo)
VALUES ('00456', 'DANNESY', '2026-09-01')
ON CONFLICT(atm_numero, periodo)
DO UPDATE SET responsable = excluded.responsable;

COMMIT;
```

Una segunda carga del mismo mes actualiza la responsable, sin borrar atenciones ni cierres. Para el mes siguiente usar otra fecha; se crea un mantenimiento nuevo y se conserva el anterior. Omitir un ATM en una carga no elimina su registro existente.

No usar `INSERT OR REPLACE`, `DROP TABLE`, `DELETE` ni el modo “reemplazar tabla” de herramientas ETL: pueden destruir IDs e historial. Usar `INSERT … ON CONFLICT … DO UPDATE` como arriba. Si una fila falla, hacer `ROLLBACK` de la carga completa. Si la herramienta realiza un commit por fila, desactivar ese comportamiento para conservar atomicidad.

El número de ATM y el período son inmutables después de crear la fila; corregir la fuente antes de cargar. Las reasignaciones afectan solo ese ATM y mes. La responsable anterior pierde acceso a todo el mantenimiento de ese período y la nueva recibe el historial completo. Otros meses no cambian.

## Ejemplo desde Python / tu ETL

```python
import sqlite3

periodo = '2026-09-01'  # Parámetro de la campaña
filas = [('00123', 'Romina'), ('00456', 'Dannesy')]
conn = sqlite3.connect('db.sqlite3', timeout=20)
try:
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('BEGIN IMMEDIATE')
    conn.executemany('''
        INSERT INTO mantenimientos (atm_numero, responsable, periodo)
        VALUES (?, ?, ?)
        ON CONFLICT(atm_numero, periodo)
        DO UPDATE SET responsable = excluded.responsable
    ''', [(str(atm).strip(), responsable.strip().upper(), periodo)
          for atm, responsable in filas])
    conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()
```

Validar duplicados en la fuente antes de ejecutar: si repites el mismo ATM con responsables distintos, el último `UPSERT` determina su asignación. Los ceros ya perdidos en una fuente numérica no se recuperan automáticamente: tratar el ATM como texto desde el origen.

## Cuentas y visibilidad

La tabla `responsables` contiene los tres códigos. `usuario_id` vincula cada código a una cuenta Django; el administrador configura este vínculo desde `/admin/`. Un usuario sin vínculo no ve ATM. Solo un superusuario ve todas las asignaciones. Marcar únicamente “staff” no concede visibilidad global en la app.

La interfaz vuelve a consultar SQLite al recargar o filtrar. No hay proceso de importación ni sincronización intermedia, ni actualización automática sin recargar. Las atenciones se guardan en `atenciones`, con autor y momento de registro. Django guarda los instantes en UTC y la interfaz los muestra en `America/Lima`.

SQLite es la base local del único servidor Django. Las responsables acceden por navegador; no abren copias del archivo. Mantener la base activa fuera de carpetas sincronizadas. Para una copia consistente, usar la API `sqlite3.Connection.backup` con la aplicación en funcionamiento o copiar la base cuando no haya escritores activos.
