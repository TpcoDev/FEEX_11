.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
Chilean Delivery Guide
======================

Enhancements over other forks:
 * Multilocalization (in progress)
 * Usability details:
    * *Stock Picking validation disengaged from dispatch guide generation:* so that you can generate a picking and after its validation, decide to create the dispatch guide.
    * *DTE Tab appears only if dte is generated* Disable unuseful data from your form.
    * *Picking number and dispatch number coexists:* This way you can use both references for different purposes, and dispatch guide number does not overwrite Odoo's natural order (less invasive).
    * *Dispatch guide cancellation:* if you generated a guide by error, you can roll it back whenever it has not been sent to SII.

Installation
============

* Install this app.
* Requires fleet management
* Requires to configure *locations* in inventory app

Configuration
=============

To configure this module, you need to enable locations in inventory app:
 * Go to *Settings > Inventory > Locations (check)*
 * Once in locations, you cann add the following:
    * Branch SII code
    * Sequence for delivery guide
    * (sii) Document type (delivery guide == "guia de despacho")


Known issues / Roadmap
======================

AUTHOR
=======
Daniel Santibañez Polanco, Cooperativa Odoocoop

This module has been forked from http://github.com/dansanti/l10n_cl_stock_delivery_guide
Which uses part of our previous code.
This code is mantained by Blanco Martín & Asociados as part of a new version localization.


Credits & Contributors
----------------------

* Blanco Martín & Asociados Development Task Force <dev@bmya.cl>
* Daniel Blanco <daniel@bmya.cl>
* Daniel Santibañez <dansanti@gmail.com>


Maintainer
----------
Blanco Martín & Asociados

This module (fork) is maintained by Blanco Martín & Asociados.

To contribute to this module, please visit https://blancomartin.cl.

.. image:: https://blancomartin.cl/logo.png
   :alt: Blanco Martin y Asociados' logo
   :target: https://blancomartin.cl
