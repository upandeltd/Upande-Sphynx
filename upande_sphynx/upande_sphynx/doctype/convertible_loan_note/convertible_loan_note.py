# Copyright (c) 2025, Jeniffer and contributors
# For license information, please see license.txt

# import frappe
# ============================================
# CONVERTIBLE LOAN NOTE - CLEAN ON_CANCEL
# ============================================
# Add this to convertible_loan_note.py

from frappe.model.document import Document
import frappe
from frappe import _

class ConvertibleLoanNote(Document):
    
    def on_cancel(self):
        """
        Clean cancellation approach:
        1. Clear all link references in CLN
        2. Delete dynamic links
        3. Cancel all linked documents
        4. Update shareholder
        """
        
        # Step 1: Clear all link field references in CLN document
        self.clear_link_references()
        
        # Step 2: Delete any dynamic links
        self.remove_dynamic_links()
        
        # Step 3: Cancel all linked documents
        self.cancel_linked_documents()
        
        # Step 4: Update shareholder
        self.update_shareholder_on_cancel()
        
        # Step 5: Update status
        self.db_set("status", "Cancelled", update_modified=False)
        
        frappe.db.commit()
    
    def clear_link_references(self):
        """Clear all link fields that point to Journal Entries and Share Movement"""
        
        # Store references before clearing (for cancellation)
        self._cached_refs = {
            'disbursement_je': self.disbursement_journal_entry_ref,
            'conversion_je': self.conversion_journal_entry_ref,
            'share_movement': self.share_transfer_ref,
            'interest_accruals': []
        }
        
        # Cache interest accrual JEs
        if hasattr(self, 'interest_accruals') and self.interest_accruals:
            for accrual in self.interest_accruals:
                if accrual.journal_entry:
                    self._cached_refs['interest_accruals'].append(accrual.journal_entry)
        
        # Clear the link fields using db_set (works on submitted docs)
        frappe.db.set_value("Convertible Loan Note", self.name, {
            "disbursement_journal_entry_ref": None,
            "conversion_journal_entry_ref": None,
            "share_transfer_ref": None
        }, update_modified=False)
        
        # Clear JE references in child table
        if hasattr(self, 'interest_accruals') and self.interest_accruals:
            for accrual in self.interest_accruals:
                frappe.db.set_value("CLN Interest Accrual", accrual.name, 
                                  "journal_entry", None, update_modified=False)
        
        frappe.db.commit()
        
        print(f"✓ Cleared link references for {self.name}")
    
    def remove_dynamic_links(self):
        """Remove any dynamic links between CLN and Journal Entries"""
        
        # Delete from Dynamic Link table if it exists
        if frappe.db.exists("DocType", "Dynamic Link"):
            frappe.db.sql("""
                DELETE FROM `tabDynamic Link`
                WHERE parent = %s 
                AND parenttype = 'Convertible Loan Note'
            """, self.name)
            
            frappe.db.commit()
            print(f"✓ Removed dynamic links for {self.name}")
    
    def cancel_linked_documents(self):
        """Cancel all linked documents using cached references"""
        
        refs = getattr(self, '_cached_refs', {})
        cancelled = []
        
        # 1. Cancel Share Movement (if converted)
        if refs.get('share_movement'):
            try:
                sm = frappe.get_doc("Share Movement", refs['share_movement'])
                if sm.docstatus == 1:
                    # Clear its JE reference first
                    if sm.journal_entry_ref:
                        frappe.db.set_value("Share Movement", sm.name, 
                                          "journal_entry_ref", None, update_modified=False)
                    sm.reload()
                    sm.flags.ignore_links = True
                    sm.cancel()
                    cancelled.append(f"Share Movement {sm.name}")
            except Exception as e:
                frappe.log_error(f"Error cancelling Share Movement: {str(e)}")
        
        # 2. Cancel Conversion JE
        if refs.get('conversion_je'):
            try:
                je = frappe.get_doc("Journal Entry", refs['conversion_je'])
                if je.docstatus == 1:
                    je.flags.ignore_links = True
                    je.cancel()
                    cancelled.append(f"Conversion JE {je.name}")
            except Exception as e:
                frappe.log_error(f"Error cancelling Conversion JE: {str(e)}")
        
        # 3. Cancel Interest Accrual JEs
        for je_name in refs.get('interest_accruals', []):
            try:
                je = frappe.get_doc("Journal Entry", je_name)
                if je.docstatus == 1:
                    je.flags.ignore_links = True
                    je.cancel()
                    cancelled.append(f"Interest JE {je.name}")
            except Exception as e:
                frappe.log_error(f"Error cancelling Interest JE {je_name}: {str(e)}")
        
        # 4. Cancel Disbursement JE
        if refs.get('disbursement_je'):
            try:
                je = frappe.get_doc("Journal Entry", refs['disbursement_je'])
                if je.docstatus == 1:
                    je.flags.ignore_links = True
                    je.cancel()
                    cancelled.append(f"Disbursement JE {je.name}")
            except Exception as e:
                frappe.log_error(f"Error cancelling Disbursement JE: {str(e)}")
        
        if cancelled:
            print(f"✓ Cancelled: {', '.join(cancelled)}")
        
        frappe.db.commit()
    
    def update_shareholder_on_cancel(self):
        """Update shareholder totals after cancellation"""
        
        if not self.lender:
            return
        
        try:
            # Recalculate active CLN total (excluding this one)
            active_cln_total = frappe.db.sql("""
                SELECT SUM(principal_amount)
                FROM `tabConvertible Loan Note`
                WHERE lender = %s 
                AND status = 'Active' 
                AND docstatus = 1
                AND name != %s
            """, (self.lender, self.name))[0][0] or 0
            
            shareholder = frappe.get_doc("Shareholder", self.lender)
            shareholder.custom_total_cln_amount = active_cln_total
            shareholder.custom_has_convertible_loans = 1 if active_cln_total > 0 else 0
            shareholder.flags.ignore_permissions = True
            shareholder.save()
            
            print(f"✓ Updated shareholder {self.lender}")
        except Exception as e:
            frappe.log_error(f"Error updating shareholder: {str(e)}")
    
    def on_trash(self):
        """Clean up when deleting cancelled CLN"""
        
        if self.docstatus != 2:
            frappe.throw(_("Only cancelled documents can be deleted"))
        
        # Get all linked document references
        linked_docs = []
        
        if self.share_transfer_ref:
            linked_docs.append(("Share Movement", self.share_transfer_ref))
        
        if self.conversion_journal_entry_ref:
            linked_docs.append(("Journal Entry", self.conversion_journal_entry_ref))
        
        if hasattr(self, 'interest_accruals') and self.interest_accruals:
            for accrual in self.interest_accruals:
                if accrual.journal_entry:
                    linked_docs.append(("Journal Entry", accrual.journal_entry))
        
        if self.disbursement_journal_entry_ref:
            linked_docs.append(("Journal Entry", self.disbursement_journal_entry_ref))
        
        # Delete all linked cancelled documents
        for doctype, docname in linked_docs:
            try:
                if frappe.db.exists(doctype, docname):
                    doc = frappe.get_doc(doctype, docname)
                    if doc.docstatus == 2:  # Only delete cancelled
                        frappe.delete_doc(doctype, docname, force=1, ignore_permissions=True)
                        print(f"✓ Deleted {doctype} {docname}")
            except Exception as e:
                frappe.log_error(f"Error deleting {doctype} {docname}: {str(e)}")
        
        frappe.db.commit()
    
    def before_delete(self):
        """Prevent deletion of submitted documents"""
        if self.docstatus == 1:
            frappe.throw(_("Cannot delete submitted Convertible Loan Note. Please cancel first."))
