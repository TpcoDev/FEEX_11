
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================================
Módulo base de Contabilidad Chile
=================================

#. Create a purchases journals for "Liquidación de Impuestos", "Asientos de Apertura / Cierre" and "Sueldos y Jornales"
on chart account installation

Esta implementación está basada en la implementación de módulo similar de Argentina (l10n_ar_account) con el objeto de
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


Configuration
=============

Simply install

Usage
=====

Add partner data, related to Chilean Localization (RUT with validation, Tax Payer Type, reformat of addresses, etc).

Known issues / Roadmap
======================

Author
======
Author: Blanco Martín & Asociados. Based on Adhoc S.A. "l10n_ar_account" implementation.

Credits and Contributors
========================

* BMyA Development Task Force: <dev@blancomartin.cl>
* Daniel Blanco <daniel@blancomartin.cl>
* Juan José Scarafía <jjs@adhoc.com.ar>
* ADHOC SA
* Moldeo Interactive
* Odoo Community Association (OCA)'
* Susana Vázquez <svazquez@netquest.com>


Maintainer
==========

Blanco Martín & Asociados - Odoo Silver Partner 2018.

.. image:: https://blancomartin.cl/logo.png
   :alt: Blanco Martin y Asociados' logo
   :target: https://blancomartin.cl


This module is maintained by Blanco Martín & Asociados.

To contribute to this module, please visit https://blancomartin.cl.
