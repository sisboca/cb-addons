# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from odoo.tests.common import TransactionCase
from odoo import exceptions


class TestInvoiceIntegrationPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.state = self.env["res.country.state"].create(
            {
                "name": "Ciudad Real",
                "code": "13",
                "country_id": self.ref("base.es"),
            }
        )
        self.partner = self.env["res.partner"].create(
            {
                "name": "NAME",
                "street": "C/ Ejemplo, 13",
                "zip": "13700",
                "city": "Tomelloso",
                "state_id": self.state.id,
                "country_id": self.ref("base.es"),
                "email": "noreply@test.com",
                "vat": "ES05680675C",
                "facturae": True,
                "organo_gestor": "1",
                "unidad_tramitadora": "1",
                "oficina_contable": "1",
                "invoice_integration_method_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref(
                                "invoice_integration_email.integration_email"
                            ).id
                        ],
                    )
                ],
            }
        )
        main_company = self.env.ref("base.main_company")
        main_company.vat = "ESA12345674"
        main_company.partner_id.country_id = self.ref("base.uk")
        main_company.currency_id = self.ref("base.EUR")
        self.payment_method = self.env["account.payment.method"].create(
            {
                "name": "inbound_mandate",
                "code": "inbound_mandate",
                "payment_type": "inbound",
                "bank_account_required": False,
                "mandate_required": True,
                "active": True,
            }
        )
        payment_methods = self.env["account.payment.method"].search(
            [("payment_type", "=", "inbound")]
        )
        self.journal = self.env["account.journal"].create(
            {
                "name": "Test journal",
                "code": "TEST",
                "type": "bank",
                "company_id": main_company.id,
                "inbound_payment_method_ids": [(6, 0, payment_methods.ids)],
            }
        )
        self.payment_mode = self.env["account.payment.mode"].create(
            {
                "name": "Test payment mode",
                "bank_account_link": "fixed",
                "fixed_journal_id": self.journal.id,
                "payment_method_id": self.env.ref(
                    "payment.account_payment_method_electronic_in"
                ).id,
                "facturae_code": "01",
            }
        )

        self.payment_mode_02 = self.env["account.payment.mode"].create(
            {
                "name": "Test payment mode 02",
                "bank_account_link": "fixed",
                "fixed_journal_id": self.journal.id,
                "payment_method_id": self.payment_method.id,
                "facturae_code": "02",
            }
        )
        self.env["res.currency.rate"].search(
            [("currency_id", "=", main_company.currency_id.id)]
        ).write({"company_id": False})
        bank_obj = self.env["res.partner.bank"]
        self.bank = bank_obj.search(
            [("acc_number", "=", "BE96 9988 7766 5544")], limit=1
        )
        if not self.bank:
            self.bank = bank_obj.create(
                {
                    "state": "iban",
                    "acc_number": "BE96 9988 7766 5544",
                    "partner_id": self.partner.id,
                    "bank_id": self.env["res.bank"]
                    .search([("bic", "=", "PSSTFRPPXXX")], limit=1)
                    .id,
                }
            )
        self.mandate = self.env["account.banking.mandate"].create(
            {
                "company_id": main_company.id,
                "format": "basic",
                "partner_id": self.partner.id,
                "state": "valid",
                "partner_bank_id": self.bank.id,
                "signature_date": "2016-03-12",
            }
        )

        account = self.env["account.account"].create(
            {
                "company_id": main_company.id,
                "name": "Facturae Product account",
                "code": "facturae_product",
                "user_type_id": self.env.ref(
                    "account.data_account_type_revenue"
                ).id,
            }
        )
        self.invoice = self.env["account.invoice"].create(
            {
                "partner_id": self.partner.id,
                "account_id": self.partner.property_account_receivable_id.id,
                "journal_id": self.journal.id,
                "date_invoice": "2016-03-12",
                "partner_bank_id": self.bank.id,
                "payment_mode_id": self.payment_mode.id,
            }
        )
        main_company.facturae_cert_password = "password"
        self.tax = self.env["account.tax"].create(
            {
                "name": "Test tax",
                "amount_type": "percent",
                "amount": 21,
                "type_tax_use": "sale",
                "facturae_code": "01",
            }
        )
        self.invoice_line = self.env["account.invoice.line"].create(
            {
                "product_id": self.env.ref("product.product_delivery_02").id,
                "account_id": account.id,
                "invoice_id": self.invoice.id,
                "name": "Producto de prueba",
                "quantity": 1.0,
                "price_unit": 100.0,
                "invoice_line_tax_ids": [(6, 0, self.tax.ids)],
            }
        )
        self.invoice._onchange_invoice_line_ids()
        self.invoice.action_invoice_open()
        self.invoice.number = "R/0001"

    def test_process(self):
        self.invoice.action_integrations()
        integration = self.env["account.invoice.integration"].search(
            [("invoice_id", "=", self.invoice.id)]
        )
        self.assertEqual(integration.method_id.code, "email")
        self.assertEqual(integration.can_send, True)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "attach.txt",
                "datas": base64.b64encode("attachment".encode("utf-8")),
                "datas_fname": "attach.txt",
                "res_model": "account.invoice",
                "res_id": self.invoice.id,
                "mimetype": "text/plain",
            }
        )
        integration.attachment_ids = [(6, 0, attachment.ids)]
        integration.send_action()
        self.assertEqual(integration.state, "sent")
        with self.assertRaises(exceptions.UserError):
            integration.update_action()
        with self.assertRaises(exceptions.ValidationError):
            self.env["account.invoice.integration.cancel"].create(
                {"integration_id": integration.id}
            ).cancel_integration()
        return integration

    def test_process_email(self):
        self.partner.email_integration = "test@test.com"
        self.test_process()

    def test_process_report(self):
        self.partner.invoice_report_email_id = self.browse_ref(
            "account.account_invoices_without_payment"
        )
        self.test_process()
