# Copyright (c) 2025, Jeniffer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from upande_sphynx.api.capital_management import recalculate_shareholder_totals

# Movement types that increase a shareholder's holding and should get certificate numbers.
ISSUANCE_MOVEMENT_TYPES = ["Equity Capital Injection", "Share Purchase", "Loan Equity Injection"]


class ShareMovement(Document):

    def validate(self):
        self.validate_source_document()
        self.generate_certificate_numbers()

        # Opening entries never get a Journal Entry — don't let the checkbox
        # claim otherwise, regardless of what the client sent.
        if self.is_opening_entry == "Yes" and self.auto_create_journal_entry:
            self.auto_create_journal_entry = 0

    def validate_source_document(self):
        """Validate that certain movement types must come from source documents"""

        # A conversion from a Convertible Loan Note must reference that CLN
        if self.movement_type == "Loan Equity Injection":
            if not self.source_document_type or self.source_document_type != "Convertible Loan Note":
                frappe.throw(_(
                    "Loan Equity Injection movements can only be created from a Convertible Loan Note. "
                    "Please use the 'Convert to Shares' button in the CLN document."
                ))

            if not self.source_document_name:
                frappe.throw(_("Please specify the source Convertible Loan Note"))

            if not frappe.db.exists("Convertible Loan Note", self.source_document_name):
                frappe.throw(_("Source Convertible Loan Note {0} does not exist").format(self.source_document_name))

        # Equity Capital Injection should typically come from a Share Agreement (warning only)
        if self.movement_type == "Equity Capital Injection":
            if not self.source_document_type or self.source_document_type != "Share Agreement":
                frappe.msgprint(
                    _("Warning: Equity Capital Injection should typically be created from a Share Agreement using the 'Issue Shares' button. "
                      "Manual creation may lead to incomplete records."),
                    indicator="orange",
                    alert=True
                )

            if self.source_document_name and not frappe.db.exists("Share Agreement", self.source_document_name):
                frappe.throw(_("Source Share Agreement {0} does not exist").format(self.source_document_name))

    def generate_certificate_numbers(self):
        """Auto-generate certificate numbers if not provided"""

        # Only generate for new documents, and only for movements that issue new shares
        if not (self.is_new() and not self.certificate_numbers and self.movement_type in ISSUANCE_MOVEMENT_TYPES):
            return

        last_cert = frappe.db.sql("""
            SELECT certificate_numbers
            FROM `tabShare Movement`
            WHERE company = %s
            AND share_class = %s
            AND certificate_numbers IS NOT NULL
            AND certificate_numbers != ''
            ORDER BY creation DESC
            LIMIT 1
        """, (self.company, self.share_class))

        start_num = 1
        if last_cert and last_cert[0][0]:
            try:
                last_cert_str = last_cert[0][0]
                last_num_str = last_cert_str.split(",")[-1].strip()
                if "-" in last_num_str:
                    start_num = int(last_num_str.split("-")[-1]) + 1
            except Exception:
                start_num = 1

        shares_per_cert = 100  # Can be customized
        num_certificates = max(1, (self.number_of_shares + shares_per_cert - 1) // shares_per_cert)

        cert_numbers = []
        for i in range(num_certificates):
            cert_num = "CERT-{0}-{1:05d}".format(self.share_class or "SHARE", start_num + i)
            cert_numbers.append(cert_num)

        self.certificate_numbers = ", ".join(cert_numbers)

        frappe.msgprint(
            _("Certificate Numbers auto-generated: {0}").format(self.certificate_numbers),
            indicator="green",
            alert=True
        )

    def on_submit(self):
        """Keep the to/from Shareholder's holdings and investment totals
        current, and auto-create the Journal Entry if the user opted in via
        "Auto-create Journal Entry on Submit" (never for Opening Entries —
        validate() already forces the checkbox off for those)."""
        recalculate_shareholder_totals(self.to_shareholder)
        if self.from_shareholder:
            recalculate_shareholder_totals(self.from_shareholder)

        if self.auto_create_journal_entry and not self.journal_entry_ref:
            from upande_sphynx.api.capital_management import create_journal_entry_from_share_movement
            try:
                create_journal_entry_from_share_movement(self.name)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Share Movement auto Journal Entry creation failed")
                frappe.msgprint(
                    _("Could not automatically create the Journal Entry for this Share Movement — "
                      "use Create Journal Entry from the Actions menu instead."),
                    indicator="orange",
                    alert=True
                )

    def on_cancel(self):
        """Handle cancellation - cancel linked JE and clear references"""
        if self.journal_entry_ref:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry_ref)
                if je.docstatus == 1:
                    je.cancel()
            except Exception as e:
                frappe.log_error(f"Error cancelling linked Journal Entry: {str(e)}", "Share Movement on_cancel")

        # Clear reference in Share Agreement / Convertible Loan Note if linked
        self.detach_from_source_document(reset_status="Draft" if self.source_document_type == "Share Agreement" else "Active")

        self.db_set("status", "Cancelled", update_modified=False)

        recalculate_shareholder_totals(self.to_shareholder)
        if self.from_shareholder:
            recalculate_shareholder_totals(self.from_shareholder)

    def detach_from_source_document(self, reset_status):
        """Clear the back-reference on the Share Agreement / Convertible Loan Note
        this movement came from. Must run before deletion (in on_trash, not
        before_delete — see on_trash's docstring) so Frappe's own link check
        doesn't block deleting this movement while something still points to it."""
        if self.source_document_type == "Share Agreement" and self.source_document_name:
            if frappe.db.exists("Share Agreement", self.source_document_name):
                frappe.db.set_value("Share Agreement", self.source_document_name, {
                    "share_movement_ref": None,
                    "status": reset_status
                }, update_modified=False)

        if self.source_document_type == "Convertible Loan Note" and self.source_document_name:
            if frappe.db.exists("Convertible Loan Note", self.source_document_name):
                frappe.db.set_value("Convertible Loan Note", self.source_document_name, {
                    "share_transfer_ref": None,
                    "status": reset_status
                }, update_modified=False)

    def on_trash(self):
        """Clean up linked JE, and detach from any source document, when
        deleting a Share Movement (Draft or Cancelled).

        Detaching here — rather than in before_delete — matters: Frappe runs
        on_trash *before* its own check for other documents still linking to
        this one (frappe/model/delete_doc.py). A Share Agreement's
        share_movement_ref, or a Convertible Loan Note's share_transfer_ref,
        pointing at this movement would otherwise block the delete outright,
        regardless of this movement's own status. (Note: `before_delete` is
        not an actual Frappe hook — a version of this file used to define
        one, but Frappe never calls it; removed.)
        """
        self.detach_from_source_document(reset_status="Draft" if self.source_document_type == "Share Agreement" else "Active")

        if self.docstatus == 2 and self.journal_entry_ref:
            try:
                if frappe.db.exists("Journal Entry", self.journal_entry_ref):
                    je = frappe.get_doc("Journal Entry", self.journal_entry_ref)
                    if je.docstatus == 2:
                        frappe.delete_doc("Journal Entry", je.name, force=1)
            except Exception:
                # don't block trashing if cleanup fails
                pass
