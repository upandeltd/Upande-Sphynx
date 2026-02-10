# Copyright (c) 2025, Jeniffer and contributors
# For license information, please see license.txt

# import frappe
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
    
    def before_delete(self):
        """Prevent deletion of submitted documents"""
        if self.docstatus == 1:
            frappe.throw(_("Cannot delete submitted Share Agreement. Please cancel first."))
    
    def on_trash(self):
        """Clean up linked documents when deleting cancelled document"""
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
                            except:
                                pass
                        
                        frappe.delete_doc("Share Movement", sm.name, force=1)
                except:
                    pass

