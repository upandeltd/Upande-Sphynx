# Copyright (c) 2025, Jeniffer and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ShareAgreement(Document):

    def on_cancel(self):
        """Handle cancellation - cancel linked documents"""
        # Cancel linked Share Movement
        if self.share_movement_ref:
            try:
                sm = frappe.get_doc("Share Movement", self.share_movement_ref)
                if sm.docstatus == 1:
                    # Cancel JE first if it exists
                    if sm.journal_entry_ref:
                        je = frappe.get_doc("Journal Entry", sm.journal_entry_ref)
                        if je.docstatus == 1:
                            je.cancel()
                    
                    # Then cancel Share Movement
                    sm.cancel()
            except Exception as e:
                frappe.log_error(f"Error cancelling linked Share Movement: {str(e)}")
        
        # Reset status
        self.db_set("status", "Cancelled", update_modified=False)
    
    def on_trash(self):
        """Clean up linked documents when deleting cancelled document.

        Deleting the linked Share Movement here uses force=1, which skips
        Frappe's own cross-document link check — needed since the Share
        Movement's own source_document_name (a Dynamic Link) points back at
        this Agreement, and would otherwise block this Agreement's deletion.
        The reverse direction — deleting the Share Movement first — is
        handled by ShareMovement.on_trash detaching this reference before
        Frappe's link check runs.
        """
        if self.docstatus == 2:  # Cancelled
            # Delete linked Share Movement if cancelled
            if self.share_movement_ref:
                try:
                    sm = frappe.get_doc("Share Movement", self.share_movement_ref)
                    if sm.docstatus == 2:
                        # Delete linked JE first
                        if sm.journal_entry_ref:
                            try:
                                if frappe.db.exists("Journal Entry", sm.journal_entry_ref):
                                    je = frappe.get_doc("Journal Entry", sm.journal_entry_ref)
                                    if je.docstatus == 2:
                                        frappe.delete_doc("Journal Entry", je.name, force=1)
                            except Exception:
                                frappe.log_error(frappe.get_traceback(), "Share Agreement on_trash: JE cleanup failed")

                        frappe.delete_doc("Share Movement", sm.name, force=1)
                except Exception:
                    frappe.log_error(frappe.get_traceback(), "Share Agreement on_trash: Share Movement cleanup failed")

