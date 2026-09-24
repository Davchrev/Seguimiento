# Seguimiento de mantenimiento preventivo ATM

App Django 5.2 y SQLite. Cada responsable ve tarjetas con sus ATM, registra varias atenciones con fecha, hora y observación y realiza un cierre final por mes. El administrador gestiona cuentas y asignaciones. La carga masiva se hace directamente contra SQLite desde tu ETL; no existe importación de archivos en la interfaz.

## Inicio

Python 3.12 o superior. Desde la carpeta del proyecto:

```sh
python -m venv .venv
```

Activar el entorno:

```sh
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell (usar esta línea en vez de la anterior)
.venv\Scripts\Activate.ps1
```

```sh
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py preparar_cuentas
python manage.py runserver 127.0.0.1:8000
```

Abrir http://127.0.0.1:8000. En esta máquina también puedes usar el entorno existente `/Users/davidchavezrevoredo/Documents/EntVirt/env/bin/python` en lugar de crear uno nuevo.

Las cuentas `romina`, `dannesy` y `rosaura` se preparan **sin contraseña utilizable**. Entra como administrador a `/admin/`, abre cada usuario y asigna su contraseña con el enlace de cambio de contraseña. También puedes ejecutar `python manage.py changepassword romina` (y repetir para las otras dos). No hay contraseñas predeterminadas ni ATM ficticios en la base inicial.

## Funcionamiento

- Un mantenimiento por ATM y mes; el ATM es texto para conservar ceros iniciales.
- El período se elige en el tablero. Cada mes conserva sus asignaciones, atenciones y cierre.
- Pendiente: cero atenciones. En curso: al menos una atención. Cerrado: fecha y hora final registrada.
- La observación es obligatoria por atención y opcional en el cierre.
- El cierre requiere al menos una atención y no puede preceder a la última. No se aceptan fechas futuras ni anteriores al mes de la campaña. Se permite completar una campaña en un mes posterior.
- Al cerrar, no se agregan ni editan atenciones. El historial sigue visible. Esta versión no tiene reapertura ni eliminación desde la interfaz.
- Se verifican permisos también en URLs y formularios, no solo en las tarjetas. Un usuario sin responsable vinculada no ve ningún ATM. Solo el superusuario tiene vista global.
- Las escrituras se ejecutan en transacciones SQLite `IMMEDIATE`. La asignación y el estado se revisan dentro de la transacción. Cada envío de atención lleva un identificador único para evitar duplicados por reenvío del mismo formulario.
- El administrador puede agregar una asignación manualmente en `/admin/` o cambiar su responsable. El ETL usa la misma tabla. No se puede cambiar el número ni el mes de un mantenimiento ya creado.

## Tu carga SQL

La tabla destino es `mantenimientos`, columnas **`atm_numero`, `responsable`, `periodo`**. La fuente puede tener solo ATM y Responsable; el ETL añade el mes como parámetro. [Contrato y ejemplos SQL/Python](docs/ETL.md).

## Verificación

```sh
python manage.py check
python manage.py test
```

Las pruebas usan una base temporal: cubren aislamiento de usuarios, carga directa SQL, reasignación, unicidad mensual, registro, reenvíos, fechas y bloqueo del cierre.

## Acceso desde otras PC

Para una prueba en red local, configurar `DJANGO_ALLOWED_HOSTS` con el nombre o IP de la PC anfitriona, además de `localhost,127.0.0.1`, y ejecutar `python manage.py runserver 0.0.0.0:8000`. Las responsables entran a `http://IP-DEL-SERVIDOR:8000`; requiere conectividad y permiso de firewall. No usar `runserver` como servidor permanente.

Para despliegue permanente configurar un servidor WSGI compatible con el sistema anfitrión, HTTPS, `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` y los hosts permitidos; ejecutar `collectstatic` y servir los estáticos. En modo producción las cookies son seguras y se redirige a HTTPS. La configuración predeterminada es local, no un despliegue en la red corporativa.

Variables: `SQLITE_PATH` (ruta del archivo), `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` (separados por comas). Se leen del entorno del proceso; no se carga `.env` automáticamente. En desarrollo se genera `.secret_key` local, excluida de Git, al primer inicio.

Referencias de implementación: [autenticación Django](https://docs.djangoproject.com/en/5.2/topics/auth/default/) y [transacciones Django](https://docs.djangoproject.com/en/5.2/topics/db/transactions/).
