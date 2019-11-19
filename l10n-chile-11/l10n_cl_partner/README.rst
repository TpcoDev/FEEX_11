.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

===============================================================================
Títulos de Personería y Tipos de documentos Chilenos relacionado con 'partners'
===============================================================================

Esta implementación está basada en la implementación de módulo similar de Argentina (l10n_ar_partner) con el objeto de
que ambas localizaciones puedan coexistir en una misma base de datos, asignando cada localización a sendas compañías.
Se ha hecho un esfuerzo por aunar y reutilizar los modelos de datos que provienen de las implementaciónes:
* oca/partner-contact
* account-financial-tools/account_document

y de intentar una manera preparar el terreno para:

- Ser lo menos invasivo posible sobre los modelos de Odoo
- Ser lo más genérico posible sobre los tipos de nuevos datos.
- Minimizar la interacción entre localizaciones, identificando en la medida que se pueda

Esa es la filosofía con la cual se concibe esta implementación. Sin embargo, requiere un esfuerzo adicional lograr el objetivo
buscado.

Author
======
Blanco Martín & Asociados - Based on Adhoc's "l10n_ar_partner" implementation.

Credits & Contributors
----------------------

* Blanco Martín & Asociados Development Task Force <dev@bmya.cl>
* Daniel Blanco <daniel@bmya.cl>
* Victor Inojosa <victor@bmya.cl>
* Juan José Scarafía <jjs@adhoc.com.ar>
* Moldeo Interactive
* Susana Vázquez <svazquez@netquest.com>

Special Credit & Contribution
-----------------------------

La implementación ha sido posible gracias a aportes, soporte y sponsoreo de 'netquest.com'

Maintainer
----------

.. image:: http://blancomartin.cl/logo.png
   :alt: Blanco Martin & Asociados
   :target: http://blancomartin.cl

This module is maintained by Blanco Martín & Asociados.

