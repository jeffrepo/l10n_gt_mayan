# Mayan: crédito y permisos del POS — Odoo 18

Módulo `l10n_gt_mayan`, rama `18.0`, versión `18.0.1.0.0`.

## Regla mensual de crédito

Las facturas de un mes se pueden pagar hasta el último día del mes siguiente.
Desde el primer día del segundo mes posterior, cualquier saldo pendiente de esas
facturas impide nuevas ventas al cliente en el POS.

| Fecha de factura | Último día para pagar | Bloqueo desde |
| --- | --- | --- |
| 1, 5, 10 o 30 de septiembre de 2026 | 31 de octubre de 2026 | 1 de noviembre de 2026 |
| Cualquier día de octubre de 2026 | 30 de noviembre de 2026 | 1 de diciembre de 2026 |
| Cualquier día de diciembre de 2026 | 31 de enero de 2027 | 1 de febrero de 2027 |
| Cualquier día de enero de 2028 | 29 de febrero de 2028 | 1 de marzo de 2028 |

Se usa `invoice_date`, la fecha de emisión de la factura. No se usa un plazo de
60 días, `invoice_date_due` ni `fecha_estado_cuenta`. Los vencimientos contables
de las facturas existentes no se modifican.

El cálculo se hace en el servidor con la zona horaria del contacto de la compañía;
si no está definida, se usa `America/Guatemala` para todas las terminales.

## Qué se bloquea

- Abrir el cobro, solicitar un pago electrónico, validar la venta y enviar la comanda.
- La confirmación en el servidor también comprueba el saldo: no basta con omitir
  la validación del navegador. El rechazo se propaga antes de que Odoo capture
  errores del pago, para revertir la venta dentro de la transacción.
- La regla aplica a las ventas del cliente con cualquier forma de pago, tal como
  se solicitó. No es un límite monetario ni depende del método «a crédito».
- Se consideran facturas de cliente publicadas con saldo positivo, incluidos
  pagos parciales, de la compañía del POS y del mismo cliente comercial. Los
  contactos del mismo cliente comparten el bloqueo.
- No se incluyen borradores, cancelaciones, facturas de proveedor ni notas de
  crédito. Estas últimas desbloquean cuando se aplican y reducen el saldo de las
  facturas. Los totales se muestran separados por moneda.
- Se permiten devoluciones puras y cancelaciones de comandas. Una orden mixta con
  productos nuevos también requiere la validación, aunque el total sea negativo.
- Las ventas sin cliente identificado conservan el comportamiento estándar.
- Guardar borradores sigue permitido; no confirma una venta ni autoriza una comanda.

No hay un ajuste adicional para activar el control: queda activo al instalar o
actualizar el módulo. Cada intento consulta el saldo actual; cuando se pagan y
concilian todas las facturas que causaban el bloqueo, se permite continuar sin
reiniciar el POS. Si no se puede consultar al servidor, no se autoriza una nueva
venta para un cliente identificado.

## Migración a Odoo 18

Los recursos se cargan en `point_of_sale._assets_pos` y usan las extensiones y
servicios de Odoo 18. Se reemplazaron los parches antiguos de `SubmitOrderButton`
y `ProductScreen`. La carga de `allow_delete_line` ahora se realiza desde
`hr.employee._load_pos_data_fields`.

El permiso existente **Permitir eliminar línea** se conserva en
**Empleados > Ajustes > Asistencia/Punto de venta**. Se comprueba al eliminar una
línea desde el teclado del POS con sesión de empleado; las modificaciones normales
de cantidad, precio y descuento continúan por el flujo estándar.

## Instalación o actualización

1. Usar la rama `18.0` de `jeffrepo/l10n_gt_mayan` como carpeta del addon.
   En el repositorio padre `mayangolf16`, el submódulo debe apuntar al commit de
   esta rama. Cambiar solo `branch = main` por `branch = 18.0` en `.gitmodules`
   no actualiza por sí solo el commit del submódulo.
2. En una base de pruebas Odoo 18, instalar el módulo si todavía no está instalado,
   o actualizarlo si ya existe. No hace falta desinstalarlo.
3. Reiniciar el servicio de Odoo para cargar el Python nuevo, actualizar el módulo
   y volver a abrir la interfaz del POS en cada terminal, recargando sin caché.

Con el servicio detenido y los parámetros habituales de conexión y addons:

```bash
odoo-bin -d NOMBRE_BD -u l10n_gt_mayan --stop-after-init
```

Para una primera instalación, sustituir `-u` por `-i`. Después, iniciar el servicio.
La publicación de código en GitHub no instala ni actualiza el módulo en una base.

## Validación

Pruebas de regresión sin base de datos:

```bash
python3 tests/test_credit_standalone.py
ODOO_SOURCE_DIR=/ruta/al/codigo/odoo18 node --test tests/credit.test.mjs
```

Las pruebas Python ejecutan los métodos del módulo con un adaptador del ORM en
memoria. Cubren fechas límite, meses cortos, cambio de año, pagos, compañía,
contactos, monedas, acceso al método y rechazo del servidor antes de procesar.
Las pruebas JavaScript ejecutan los métodos reales de Odoo 18 y los parches del
módulo con dobles para red, diálogos y dispositivos. Requieren Node.js 20 o posterior.

Estos controles no sustituyen una instalación en Odoo con PostgreSQL. En la base
de pruebas verificar:

1. Facturas con saldo de septiembre: se permite hasta el 31 de octubre y se
   bloquea desde el 1 de noviembre. Simular la fecha únicamente en pruebas.
2. Facturas de octubre: se permite durante noviembre, si no existe deuda anterior.
3. Con un cajero sin permisos contables, comprobar que el aviso identifica las
   facturas y que no se envía la comanda ni se registra una venta bloqueada.
4. Pagar parcialmente: sigue bloqueado. Pagar y conciliar todo el saldo vencido:
   permite vender en el siguiente intento.
5. Abrir el cobro antes del cambio de mes y validar después: debe volver a comprobar.
6. Cambiar de cliente en la pantalla de pago y comprobar el nuevo cliente.
7. Probar desconexión, devolución, cancelación de comanda, otra compañía y el
   permiso de eliminación de líneas.
8. Confirmar el rechazo de una venta enviada directamente a `sync_from_ui`, sin
   depender del JavaScript, y que la transacción no deja venta, pago ni albarán.

Referencias utilizadas:

- [POS de Odoo 18](https://github.com/odoo/odoo/blob/18.0/addons/point_of_sale/static/src/app/store/pos_store.js).
- [Validación de pagos](https://github.com/odoo/odoo/blob/18.0/addons/point_of_sale/static/src/app/screens/payment_screen/payment_screen.js).
- [Procesamiento de órdenes en servidor](https://github.com/odoo/odoo/blob/18.0/addons/point_of_sale/models/pos_order.py).
- [Carga de empleados](https://github.com/odoo/odoo/blob/18.0/addons/pos_hr/models/hr_employee.py).
