# Copyright (c) 2025, Jeniffer and contributors
# For license information, please see license.txt

import re

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
                numbers_found = re.findall(r"-(\d{5,})\b", last_cert_str)
                if numbers_found:
                    start_num = max(int(n) for n in numbers_found) + 1
            except Exception:
                start_num = 1

        shares_per_cert = 100  # Can be customized
        num_certificates = max(1, (self.number_of_shares + shares_per_cert - 1) // shares_per_cert)
        end_num = start_num + num_certificates - 1
        share_class_label = self.share_class or "SHARE"

        # Listing every certificate out as "CERT-x-00001, CERT-x-00002, ..." blows
        # past the certificate_numbers column's size for large issuances (each
        # entry is ~30 bytes, so a few thousand certificates overflow it). Past a
        # reasonable count, collapse to a range instead of enumerating each one.
        MAX_LISTED_CERTIFICATES = 20
        if num_certificates <= MAX_LISTED_CERTIFICATES:
            cert_numbers = [
                "CERT-{0}-{1:05d}".format(share_class_label, start_num + i)
                for i in range(num_certificates)
            ]
            self.certificate_numbers = ", ".join(cert_numbers)
        else:
            self.certificate_numbers = _("CERT-{0}-{1:05d} to CERT-{0}-{2:05d} ({3} certificates)").format(
                share_class_label, start_num, end_num, num_certificates
            )

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

        # Opening Entries never get a Journal Entry (validate() already forces
        # auto_create_journal_entry off for them), so nothing else will ever
        # move their status off "Draft" — submission itself is the terminal
        # state, so mark them "Issued" right away. Non-opening entries only
        # become "Issued" once their Journal Entry is created (see
        # create_journal_entry_from_share_movement), since that's the step
        # that actually records the movement in the books.
        if self.is_opening_entry == "Yes":
            self.db_set("status", "Issued", update_modified=False)

        # If this is an amended resubmission (the cancelled original was left
        # untouched — see on_cancel), re-point the source Share Agreement /
        # Convertible Loan Note at this new document.
        if self.amended_from and self.source_document_type and self.source_document_name:
            self.relink_source_document()

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
        """Cancel forward documents (the Journal Entry this movement created).

        The prior document's `status` (e.g. Share Agreement's "Shares Issued")
        is deliberately left untouched — cancelling a Share Movement is
        normally done to amend it, not to undo the prior document. Its
        back-reference (share_movement_ref / share_transfer_ref) still has to
        be cleared, though: Frappe's own check_no_back_links_exist would
        otherwise block cancelling this movement outright while a submitted
        Share Agreement/CLN still links to it. If this movement is later
        amended and resubmitted, on_submit's relink_source_document restores
        the reference.
        """
        if self.journal_entry_ref:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry_ref)
                if je.docstatus == 1:
                    je.cancel()
            except Exception as e:
                frappe.log_error(f"Error cancelling linked Journal Entry: {str(e)}", "Share Movement on_cancel")

        self.detach_from_source_document(reset_status=None)

        self.db_set("status", "Cancelled", update_modified=False)

        recalculate_shareholder_totals(self.to_shareholder)
        if self.from_shareholder:
            recalculate_shareholder_totals(self.from_shareholder)

    def relink_source_document(self):
        """Point the source Share Agreement / Convertible Loan Note's reference
        back at this document. Used when this movement is an amended
        resubmission of a cancelled movement whose reference was cleared by
        on_cancel."""
        if self.source_document_type == "Share Agreement" and self.source_document_name:
            if frappe.db.exists("Share Agreement", self.source_document_name):
                frappe.db.set_value("Share Agreement", self.source_document_name, {
                    "share_movement_ref": self.name,
                    "status": "Shares Issued"
                }, update_modified=False)

        if self.source_document_type == "Convertible Loan Note" and self.source_document_name:
            if frappe.db.exists("Convertible Loan Note", self.source_document_name):
                frappe.db.set_value("Convertible Loan Note", self.source_document_name, {
                    "share_transfer_ref": self.name,
                    "status": "Converted"
                }, update_modified=False)

    def detach_from_source_document(self, reset_status):
        """Clear the back-reference on the Share Agreement / Convertible Loan Note
        this movement came from, so Frappe's own link check doesn't block
        cancelling/deleting this movement while something still points to it
        (must run before on_cancel's/on_trash's own back-link check — see
        their docstrings).

        `reset_status` also resets the source document's own status:
        - None (from on_cancel): leave status as-is — the source document
          isn't being undone, only detached from a movement that's about to
          be amended or otherwise redone.
        - "Draft"/"Active" (from on_trash): the movement is being permanently
          deleted, erasing this issuance/conversion's history entirely, so
          the source document is freed up for a fresh one.
        """
        if self.source_document_type == "Share Agreement" and self.source_document_name:
            if frappe.db.exists("Share Agreement", self.source_document_name):
                values = {"share_movement_ref": None}
                if reset_status is not None:
                    values["status"] = reset_status
                frappe.db.set_value("Share Agreement", self.source_document_name, values, update_modified=False)

        if self.source_document_type == "Convertible Loan Note" and self.source_document_name:
            if frappe.db.exists("Convertible Loan Note", self.source_document_name):
                values = {"share_transfer_ref": None}
                if reset_status is not None:
                    values["status"] = reset_status
                frappe.db.set_value("Convertible Loan Note", self.source_document_name, values, update_modified=False)

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
