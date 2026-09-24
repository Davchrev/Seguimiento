# Estado actual — 24 septiembre 2026

El usuario autorizó construir una app nueva de mantenimiento preventivo mensual ("GO"). Implementada con Django 5.2.17 y SQLite, con cuentas por responsable, tarjetas, varias atenciones con fecha/hora/observación y cierre final. La fuente ETL tiene ATM y Responsable; el ETL añade el período y carga directamente `mantenimientos`. No hay importación por archivos en la interfaz. Ver `README.md` y `docs/ETL.md`.

Base local inicializada en `db.sqlite3`, sin ATM ficticios. Cuentas `romina`, `dannesy`, `rosaura` vinculadas, sin contraseña utilizable; falta que el administrador defina credenciales y cree su superusuario (`createsuperuser`). Solo superusuarios tienen visibilidad global. No se implementaron métricas de disponibilidad del piloto anterior porque el alcance actual es mantenimiento preventivo mensual.

22 pruebas automatizadas pasan. La revisión visual no se completó: no hay navegador conectado al control y Safari devolvió falta de permisos de Computer Use. El servidor se inició localmente en `127.0.0.1:8000`; comprobar si sigue activo al retomar. No se hizo commit ni push de la app.

La nota siguiente se conserva como contexto histórico del piloto descartado; no describe el alcance actual.

---

# Contexto anterior — 19 septiembre 2026

El usuario pidió detener el servidor y borrar el piloto para empezar más tarde desde cero, paso a paso, con información real. El servidor fue detenido y el código y SQLite eliminados. Conservar esta nota y no reconstruir hasta que lo solicite.

## Objetivo confirmado
App web para incidencias de soporte ATM de Scotiabank Perú, con restricciones corporativas. Django en la PC del usuario, SQLite local y tres responsables accediendo por navegador desde sus propias PC. El usuario puede ejecutar Python y Django. Base central a cargar posteriormente; tablas y formato real aún no definidos. SharePoint sincronizado disponible para backups en etapa posterior, no implementados. Base activa fuera de sincronización; respaldar consistentemente más adelante.

## Responsables y permisos
DANNESY, ROMINA y ROSAURA solo deben ver sus incidencias/ATM, incluidos gráficos y rutas directas. Administrador ve todo y cambia asignaciones. La columna responsable de CADA incidencia gobierna la visibilidad. Normalmente el mismo ATM mantiene responsable, pero puede cambiarse excepcionalmente. Reasignar una incidencia quita acceso a la anterior responsable y se lo da a la nueva; no modifica otras incidencias del mismo ATM.

El piloto usaba autenticación Django. Administrador creaba incidencias; responsables editaban descripción y fechas propias, sin cambiar ID, ATM ni responsable. Estos permisos de edición fueron decisiones de implementación y deben confirmarse para el producto real. Cuentas ficticias eliminadas; definir credenciales nuevas más adelante.

## Campos y métricas
Propuesta mínima: ID único de incidencia, número ATM, descripción, responsable, fecha/hora de reporte y fecha/hora de solución opcional. Estado abierto/resuelto derivado de solución. Horario America/Lima. Validar solución >= reporte y fechas no futuras. Evitar sobrescritura de ediciones simultáneas.

Solicitudes del usuario: gráfico de duración de fallas, total de indisponibilidad de todos los ATM y gráfico circular con disponibilidad/indisponibilidad porcentual (ejemplo 99,1% / 0,9%, no valores fijos).

Duración = solución − reporte, o ahora − reporte si abierta. Para total por ATM unir intervalos superpuestos antes de sumar. Distintos ATM suman sus duraciones incluso si fallan simultáneamente.

Indisponibilidad % = tiempo de falla dentro del período / (cantidad total de ATM × duración del período) × 100. Disponibilidad = 100 − indisponibilidad. Incluir ATM sin incidencias en denominador; recortar fallas al período. Gráfico de anillo verde disponible/rojo indisponible. Administrador ve total red, responsables solo sus datos.

## Supuestos pendientes de confirmar con datos reales
No hubo respuesta específica a preguntas sobre inventario y período. Se usaron 4 ATM ficticios por responsable (12 total), editables en administración y etiquetados como demostración. No son cantidades reales. Se asumió servicio 24/7 e inventario constante. Período predeterminado mes actual hasta ahora; opciones hoy y últimos 30 días. Porcentajes con dos decimales, actualizados al recargar. Indicadores totales independientes de filtros de tabla, pero respetando permisos. Barras para las 12 incidencias de mayor duración y tabla completa.

Falta definir tablas reales, carga/actualización desde base central, inventario incluyendo equipos sin fallas, período, horarios/exclusiones, asignaciones históricas, permisos definitivos y auditoría. Ninguna integración o backup implementado.

## Entorno y despliegue
Dependencias instaladas por pedido del usuario en /Users/davidchavezrevoredo/Documents/EntVirt/env: Django 5.2.17 y dependencias. Conservar entorno compartido. No copiar entorno macOS a Windows.

Para pruebas un solo servidor Django recibe navegadores y accede al archivo SQLite, sin servidor de base de datos separado. Acceso entre PC requiere escuchar en 0.0.0.0:8000, ALLOWED_HOSTS y conectividad/puerto permitidos por TI. No validado en red bancaria. PC anfitriona debe permanecer encendida.

IP DHCP puede cambiar. Nombre de PC puede funcionar si la red lo resuelve; alternativamente TI configura DNS interno y reserva IP/actualiza DNS. Django no crea nombres DNS. No es necesario publicar en internet. Uso permanente requiere servidor de producción, HTTPS, secretos, DEBUG desactivado y cuentas reales.

## Verificación anterior
El piloto respondió localmente en 127.0.0.1:8000 y pasó 12 pruebas sobre permisos, reasignaciones, fechas, solapamientos y porcentajes. No hubo revisión visual automatizada por falta de navegador conectado. Todo el piloto se descartó por instrucción del usuario. Retomar con esta nota y la información real, sin tratar supuestos de demostración como decisiones definitivas.
