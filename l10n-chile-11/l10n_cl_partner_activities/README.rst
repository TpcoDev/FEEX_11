.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================
l10n_cl_partner_activities
==========================

Odoo - Chilean Economical Activities Tables Related to Partners
===============================================================

You can check functionality in the following blog:

http://blancomartin.cl/blog/novedades-odoo-1/post/nuevo-modulo-de-giros-odoo-localizacion-chilena-5

NOVEDADES
=========

http://www.sii.cl/ayudas/ayudas_por_servicios/1956-codigos-1959.html#1

A partir del 1ro de Noviembre de 2018, el SII ha implementado nuevos códigos de actividad económica, en el marco del
proceso de recodificación de actividades que realizan el SII y el INE, con el objetivo de homologar esta clasificación
con la que usa la ONU a nivel internacional (CIIU4).

.. image:: /l10n_cl_partner_activities/static/description/sii_pa_e02.png
   :alt: Screenshot actividades económicas y busqueda por código
   :width: 600

Si su actual código tiene correspondencia a más de una actividad económica, la recodificación le asignará solo una actividad.
Revise si corresponde a la que usted realiza habitualmente. De lo contrario, podrá solicitar su modificación a partir
del 1° de noviembre.

Si Ud es usuario de facturación electrónica, antes de emitir facturas a partir de esa fecha, deberá actualizar
los códigos de actividad económica acorde con los nuevos códigos que el SII le ha asignado.
En esta actualización, hemos incorporado los nuevos códigos de actividad económica de manera tal que los mismos puedan
ser asignados a su empresa.

En nuestra implementación, conservamos los códigos antiguos con el fin de mantener compatibilidad con implementaciones antiguas,
sin embargo recomendamos revisar esta codificación para que Ud. se cerciore que los códigos de su empresa sean iguales a
los del SII, ya que en caso de diferencias sus facturas serán rechazadas por códigos de actividad mal asignados mal asignados.

VERSIONES
=========

12.0 / 11.0 / 10.0 / 8.0 / Enterprise y Community
-------------------------------------------------

.. image:: /l10n_cl_partner_activities/static/description/sii_pa_e01.png
   :alt: Screenshot menú de configuraciones facturación
   :width: 300

Como se usa
===========

Si Ud es usuario de facturación electrónica, antes de emitir facturas a partir de esa fecha, deberá actualizar
los códigos de actividad económica acorde con los nuevos códigos que el SII le ha asignado.
En esta actualización, hemos incorporado los nuevos códigos de actividad económica de manera tal que los mismos puedan
ser asignados a su empresa.

Glosa descriptiva de la actividad econoacute;mica de contribuyente Cliente o Proveedor
el cual deberá ser indicado por el contribuyente

.. image:: /l10n_cl_partner_activities/static/description/sii_pa_e04.png
   :alt: Screenshot actividades económicas - selección de actividad en la compañía o cliente
   :width: 600

En nuestra implementación, conservamos los códigos antiguos con el fin de mantener compatibilidad con implementaciones antiguas,
sin embargo recomendamos revisar sus actividades económicas para estar seguro que los códigos de su empresa sean iguales a
los del SII, ya que en caso de diferencias sus facturas electrónicas serán rechazadas por códigos de actividad mal asignados.

Permite visualizar los códigos de actividad económica durante la asignación de las mismas a compañías y a clientes / proveedores


.. image:: /l10n_cl_partner_activities/static/description/sii_pa_e03.png
   :alt: Screenshot actividades económicas - selección de actividad en la factura
   :width: 600

Una vez instalado, en la vista de partners, al editar podrá seleccionar y guardar, todas las actividades económicas de la empresa, en una vista de etiquetas.
Esto, a su vez, le permitirá seleccionar al momento de crear una nueva factura, alguno de los giros registrados para ese cliente.

Dependencies
============

Will provide a dependency list here

Credits
=======

Blanco Martín & Asociados - Odoo Silver Partner 2018.

Contributors
============

* BMyA Development Task Force: <dev@blancomartin.cl>
* Daniel Blanco <daniel@blancomartin.cl>

Maintainer
==========

.. image:: https://blancomartin.cl/logo.png
   :alt: Blanco Martin y Asociados' logo
   :target: https://blancomartin.cl

This module is maintained by Blanco Martín & Asociados.

To contribute to this module, please visit https://blancomartin.cl.
