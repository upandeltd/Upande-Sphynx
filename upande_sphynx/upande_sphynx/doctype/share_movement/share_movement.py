# File: upande_sphynx/upande_sphynx/share_movement.py
# Add this file to your custom app

import frappe
from frappe import _

def validate_share_movement(doc, method):
    """Validate Share Movement document"""
    validate_source_document(doc)
    generate_certificate_numbers(doc)

def validate_source_document(doc):
    """Validate that certain movement types must come from source documents"""
    
    # CLN Conversion MUST come from Convertible Loan Note
    if doc.movement_type == "CLN Conversion":
        if not doc.source_document_type or doc.source_document_type != "Convertible Loan Note":
            frappe.throw(_("CLN Conversion movement type can only be created from a Convertible Loan Note. Please use the 'Convert to Shares' button in the CLN document."))
        
        if not doc.source_document_name:
            frappe.throw(_("Please specify the source Convertible Loan Note"))
        
        # Verify the CLN exists and is valid
        if not frappe.db.exists("Convertible Loan Note", doc.source_document_name):
            frappe.throw(_("Source Convertible Loan Note {0} does not exist").format(doc.source_document_name))
    
    # Share Subscription SHOULD come from Share Agreement (warning only)
    if doc.movement_type == "Share Subscription":
        if not doc.source_document_type or doc.source_document_type != "Share Agreement":
            frappe.msgprint(
                _("Warning: Share Subscription should typically be created from a Share Agreement using the 'Issue Shares' button. " +
                  "Manual creation may lead to incomplete records."),
                indicator="orange",
                alert=True
            )
        
        if doc.source_document_name:
            # Verify the Share Agreement exists
            if not frappe.db.exists("Share Agreement", doc.source_document_name):
                frappe.throw(_("Source Share Agreement {0} does not exist").format(doc.source_document_name))

def generate_certificate_numbers(doc):
    """Auto-generate certificate numbers if not provided"""
    
    # Only generate for new documents
    if doc.is_new() and not doc.certificate_numbers:
        # Only for movements that issue new shares
        if doc.movement_type in [
            "Initial Share Issuance",
            "Share Subscription",
            "CLN Conversion",
            "Bonus Issue",
            "Rights Issue"
        ]:
            # Get the last certificate number for this company and share class
            last_cert = frappe.db.sql("""
                SELECT certificate_numbers
                FROM `tabShare Movement`
                WHERE company = %s 
                AND share_class = %s
                AND certificate_numbers IS NOT NULL
                AND certificate_numbers != ''
                ORDER BY creation DESC
                LIMIT 1
            """, (doc.company, doc.share_class))
            
            start_num = 1
            if last_cert and last_cert[0][0]:
                # Extract the last number from certificate string
                try:
                    last_cert_str = last_cert[0][0]
                    # Get the last certificate number
                    last_num_str = last_cert_str.split(",")[-1].strip()
                    # Extract number from format CERT-XXX-00001
                    if "-" in last_num_str:
                        start_num = int(last_num_str.split("-")[-1]) + 1
                except:
                    start_num = 1
            
            # Generate certificate numbers
            # Create one certificate per share or group (adjust as needed)
            shares_per_cert = 100  # Can be customized
            num_certificates = max(1, (doc.number_of_shares + shares_per_cert - 1) // shares_per_cert)
            
            cert_numbers = []
            for i in range(num_certificates):
                cert_num = "CERT-{0}-{1:05d}".format(doc.share_class or "SHARE", start_num + i)
                cert_numbers.append(cert_num)
            
            doc.certificate_numbers = ", ".join(cert_numbers)
            
            frappe.msgprint(
                _("Certificate Numbers auto-generated: {0}").format(doc.certificate_numbers),
                indicator="green",
                alert=True
            )# File: upande_sphynx/upande_sphynx/share_movement.py
# Add this file to your custom app

import frappe
from frappe import _

def validate_share_movement(doc, method):
    """Validate Share Movement document"""
    validate_source_document(doc)
    generate_certificate_numbers(doc)

def validate_source_document(doc):
    """Validate that certain movement types must come from source documents"""
    
    # CLN Conversion MUST come from Convertible Loan Note
    if doc.movement_type == "CLN Conversion":
        if not doc.source_document_type or doc.source_document_type != "Convertible Loan Note":
            frappe.throw(_("CLN Conversion movement type can only be created from a Convertible Loan Note. Please use the 'Convert to Shares' button in the CLN document."))
        
        if not doc.source_document_name:
            frappe.throw(_("Please specify the source Convertible Loan Note"))
        
        # Verify the CLN exists and is valid
        if not frappe.db.exists("Convertible Loan Note", doc.source_document_name):
            frappe.throw(_("Source Convertible Loan Note {0} does not exist").format(doc.source_document_name))
    
    # Share Subscription SHOULD come from Share Agreement (warning only)
    if doc.movement_type == "Share Subscription":
        if not doc.source_document_type or doc.source_document_type != "Share Agreement":
            frappe.msgprint(
                _("Warning: Share Subscription should typically be created from a Share Agreement using the 'Issue Shares' button. " +
                  "Manual creation may lead to incomplete records."),
                indicator="orange",
                alert=True
            )
        
        if doc.source_document_name:
            # Verify the Share Agreement exists
            if not frappe.db.exists("Share Agreement", doc.source_document_name):
                frappe.throw(_("Source Share Agreement {0} does not exist").format(doc.source_document_name))

def generate_certificate_numbers(doc):
    """Auto-generate certificate numbers if not provided"""
    
    # Only generate for new documents
    if doc.is_new() and not doc.certificate_numbers:
        # Only for movements that issue new shares
        if doc.movement_type in [
            "Equity Capital Injection",
            "Share Purchase",
            "Loan Equity Injection",
            "Share Subscription",
            "CLN Conversion",
            "Bonus Issue",
            "Rights Issue"
        ]:
            # Get the last certificate number for this company and share class
            last_cert = frappe.db.sql("""
                SELECT certificate_numbers
                FROM `tabShare Movement`
                WHERE company = %s 
                AND share_class = %s
                AND certificate_numbers IS NOT NULL
                AND certificate_numbers != ''
                ORDER BY creation DESC
                LIMIT 1
            """, (doc.company, doc.share_class))
            
            start_num = 1
            if last_cert and last_cert[0][0]:
                # Extract the last number from certificate string
                try:
                    last_cert_str = last_cert[0][0]
                    # Get the last certificate number
                    last_num_str = last_cert_str.split(",")[-1].strip()
                    # Extract number from format CERT-XXX-00001
                    if "-" in last_num_str:
                        start_num = int(last_num_str.split("-")[-1]) + 1
                except:
                    start_num = 1
            
            # Generate certificate numbers
            # Create one certificate per share or group (adjust as needed)
            shares_per_cert = 100  # Can be customized
            num_certificates = max(1, (doc.number_of_shares + shares_per_cert - 1) // shares_per_cert)
            
            cert_numbers = []
            for i in range(num_certificates):
                cert_num = "CERT-{0}-{1:05d}".format(doc.share_class or "SHARE", start_num + i)
                cert_numbers.append(cert_num)
            
            doc.certificate_numbers = ", ".join(cert_numbers)
            
            frappe.msgprint(
                _("Certificate Numbers auto-generated: {0}").format(doc.certificate_numbers),
                indicator="green",
                alert=True
            )

def on_cancel(self):
    """Handle cancellation of share movement"""
    # Clear reference in source documents
    if self.source_document_type and self.source_document_name:
        frappe.db.set_value(
            self.source_document_type,
            self.source_document_name,
            "share_movement_ref",
            None,
            update_modified=False
        )