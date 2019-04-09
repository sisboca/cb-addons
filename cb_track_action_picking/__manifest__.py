# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Cb Track Action Picking',
    'summary': """
        Añade registro que guarda quien ha validado el recibo de productos""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Creu Blanca,Odoo Community Association (OCA)',
    'website': 'www.creublanca.es',
    'depends': [
        'purchase'
    ],
    'data': [
        'views/stock_picking_views.xml',
    ],
}
