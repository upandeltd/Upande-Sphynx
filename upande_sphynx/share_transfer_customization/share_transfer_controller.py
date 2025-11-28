# import frappe
# from frappe.utils import flt

# # ----------------------------------------------------------------------
# # 1. Validation logic (optional, runs on validate hook)
# # ----------------------------------------------------------------------



# def set_standard_accounts(doc):
#     """Map custom filtered accounts to ERPNext standard fields"""
#     doc.equity_or_liability_account = doc.equity_or_liability_account
#     doc.asset_account = doc.asset_account

# def calculate_rate_and_amount(doc):
#     """Recalculate rate and total amount"""
#     if doc.exchange_rate and doc.exchange_rate != 0:
#         doc.rate = flt(doc.rate_in_transaction_currency) / flt(doc.exchange_rate)
#     else:
#         doc.rate = 0
    
#     # doc.total_amount_in_transaction_currency = (
#     #     flt(doc.no_of_shares) * flt(doc.rate_in_transaction_currency)
#     # )


# # ----------------------------------------------------------------------
# # 2. Custom Journal Entry creation (called from client script)
# # ----------------------------------------------------------------------

# @frappe.whitelist()
# def create_custom_journal_entry(docname):
#     """Create or re-create Journal Entry for a submitted Share Transfer"""

#     # Get the Share Transfer document
#     doc = frappe.get_doc("Share Transfer", docname)

#     # --- Validate before proceeding ---
#     if doc.docstatus != 1:
#         frappe.throw("Please submit the Share Transfer before creating a Journal Entry.")

#     if not doc.equity_or_liability_account or not doc.asset_account:
#         frappe.throw("Both Share Capital Account and Receiving Account must be set.")

#     if not doc.total_amount_in_transaction_currency:
#         frappe.throw("Total Amount in Transaction Currency cannot be zero.")

#     # Compute base amount using exchange rate
#     base_amount = (
#         flt(doc.total_amount_in_transaction_currency) / flt(doc.exchange_rate)
#         if doc.exchange_rate else flt(doc.total_amount_in_transaction_currency)
#     )

#     # --- Create Journal Entry ---
#     je = frappe.new_doc("Journal Entry")
#     je.voucher_type = "Journal Entry"

#     # 👇 Use safe date fetching (handles missing posting_date)
#     je.posting_date = getattr(doc, "transfer_date", frappe.utils.nowdate())
#     je.company = doc.company
#     je.remark = f"Auto-created from Share Transfer {doc.name}"

#     # Line 1: Credit Share Capital Account
#     je.append("accounts", {
#         "account": doc.equity_or_liability_account,
#         "credit_in_account_currency": doc.total_amount_in_transaction_currency,
#         "account_currency": doc.transaction_currency,
#         "exchange_rate": doc.exchange_rate or 1,
#         "credit": base_amount,
#         "party_type": "Shareholder",
#         "party": doc.from_shareholder,
#         "user_remark": f"Share Transfer from {doc.from_shareholder} to {doc.to_shareholder}"
#     })

#     # Line 2: Debit Receiving Account
#     je.append("accounts", {
#         "account": doc.asset_account,
#         "debit_in_account_currency": doc.total_amount_in_transaction_currency,
#         "account_currency": doc.transaction_currency,
#         "exchange_rate": doc.exchange_rate or 1,
#         "debit": base_amount,
#         "user_remark": f"Share Transfer: {doc.name}"
#     })

#     # --- Save and submit JE ---
#     je.insert(ignore_permissions=True)
#     je.submit()

#     # --- Link JE to Share Transfer (optional custom field) ---
#     if frappe.db.has_column("Share Transfer", "custom_journal_entry"):
#         doc.db_set("custom_journal_entry", je.name)

#     return f"✅ Journal Entry <b>{je.name}</b> successfully created for Share Transfer <b>{doc.name}</b>."






# File: custom_app/custom_app/controllers/share_controller.py

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

# ----------------------------------------------------------------------
# 1. Validation logic (runs on validate hook)
# ----------------------------------------------------------------------
def set_standard_accounts(doc, method=None):
    """Map custom filtered accounts to ERPNext standard fields"""
    if doc.get('equity_or_liability_account'):
        doc.equity_or_liability_account = doc.equity_or_liability_account
    
    if doc.get('asset_account'):
        doc.asset_account = doc.asset_account


def calculate_rate_and_amount(doc, method=None):
    """
    Recalculate rate and total amount based on transaction currency
    This ensures proper conversion to company currency
    """
    company_currency = frappe.get_cached_value('Company', doc.company, 'default_currency')
    
    # Set exchange rate to 1 if same currency
    if doc.transaction_currency == company_currency:
        doc.exchange_rate = 1.0
    
    # Validate exchange rate
    if not doc.exchange_rate or doc.exchange_rate == 0:
        if doc.transaction_currency != company_currency:
            frappe.throw(_("Exchange Rate is required when transaction currency differs from company currency"))
        doc.exchange_rate = 1.0
    
    # Calculate total in transaction currency
    if doc.no_of_shares and doc.rate_in_transaction_currency:
        doc.total_amount_in_transaction_currency = flt(doc.no_of_shares) * flt(doc.rate_in_transaction_currency)
    
    # Calculate amount in company currency
    if doc.total_amount_in_transaction_currency and doc.exchange_rate:
        doc.total_amount_in_company_currency = flt(doc.total_amount_in_transaction_currency) * flt(doc.exchange_rate)
    
    # Sync with default rate and amount fields (for backward compatibility)
    if doc.rate_in_transaction_currency:
        doc.rate = flt(doc.rate_in_transaction_currency) * flt(doc.exchange_rate)
    
    if doc.total_amount_in_transaction_currency:
        doc.amount = flt(doc.total_amount_in_transaction_currency) * flt(doc.exchange_rate)


def validate_accounts(doc, method=None):
    """Validate that accounts are properly configured"""
    
    if not doc.get('transaction_currency'):
        frappe.throw(_("Transaction Currency is required"))
    
    # Validate Share Capital Account
    if doc.get('equity_or_liability_account'):
        account = frappe.db.get_value('Account', doc.equity_or_liability_account, 
                                       ['is_group', 'company', 'account_currency', 'root_type'], as_dict=1)
        
        if not account:
            frappe.throw(_("Share Capital Account {0} does not exist").format(doc.equity_or_liability_account))
        
        if account.is_group:
            frappe.throw(_("Share Capital Account cannot be a group account. Please select a ledger account."))
        
        if account.company != doc.company:
            frappe.throw(_("Share Capital Account must belong to company {0}").format(doc.company))
        
        if account.account_currency and account.account_currency != doc.transaction_currency:
            frappe.throw(_("Share Capital Account currency ({0}) must match Transaction Currency ({1})").format(
                account.account_currency, doc.transaction_currency))
        
        if account.root_type not in ['Equity', 'Liability']:
            frappe.throw(_("Share Capital Account must be an Equity or Liability account"))
    
    # Validate Receiving Account
    if doc.get('asset_account'):
        account = frappe.db.get_value('Account', doc.asset_account, 
                                       ['is_group', 'company', 'account_currency', 'root_type'], as_dict=1)
        
        if not account:
            frappe.throw(_("Receiving Account {0} does not exist").format(doc.asset_account))
        
        if account.is_group:
            frappe.throw(_("Receiving Account cannot be a group account. Please select a ledger account."))
        
        if account.company != doc.company:
            frappe.throw(_("Receiving Account must belong to company {0}").format(doc.company))
        
        if account.account_currency and account.account_currency != doc.transaction_currency:
            frappe.throw(_("Receiving Account currency ({0}) must match Transaction Currency ({1})").format(
                account.account_currency, doc.transaction_currency))
        
        if account.root_type != 'Asset':
            frappe.throw(_("Receiving Account must be an Asset account"))


# ----------------------------------------------------------------------
# 2. Custom Journal Entry creation (whitelisted method)
# ----------------------------------------------------------------------
@frappe.whitelist()
def create_custom_journal_entry(docname):
    """
    Create multi-currency Journal Entry for a submitted Share Transfer
    Called from client-side button click
    """
    # Get the Share Transfer document
    doc = frappe.get_doc("Share Transfer", docname)
    
    # --- Validate before proceeding ---
    if doc.docstatus != 1:
        frappe.throw(_("Please submit the Share Transfer before creating a Journal Entry."))
    
    # Check if JE already exists
    if doc.get('custom_journal_entry'):
        je_exists = frappe.db.exists('Journal Entry', doc.custom_journal_entry)
        if je_exists:
            frappe.throw(_("Journal Entry {0} already exists for this Share Transfer").format(
                doc.custom_journal_entry))
    
    # Validate required fields
    if not doc.get('equity_or_liability_account'):
        frappe.throw(_("Share Capital Account is required"))
    
    if not doc.get('asset_account'):
        frappe.throw(_("Receiving Account is required"))
    
    if not doc.get('total_amount_in_transaction_currency') or flt(doc.total_amount_in_transaction_currency) <= 0:
        frappe.throw(_("Total Amount in Transaction Currency must be greater than zero"))
    
    if not doc.get('transaction_currency'):
        frappe.throw(_("Transaction Currency is required"))
    
    # Get company currency
    company_currency = frappe.get_cached_value('Company', doc.company, 'default_currency')
    exchange_rate = flt(doc.exchange_rate) if doc.exchange_rate else 1.0
    
    # Validate exchange rate
    if doc.transaction_currency != company_currency and exchange_rate == 0:
        frappe.throw(_("Exchange Rate cannot be zero when currencies differ"))
    
    # --- Create Journal Entry ---
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = doc.company
    
    # Use the correct date field
    posting_date = doc.get('date') or doc.get('transfer_date') or nowdate()
    je.posting_date = posting_date
    je.cheque_date = posting_date
    je.cheque_no = doc.name
    
    je.user_remark = _('Share Transfer: {0} to {1} | {2} shares @ {3} {4} per share = {5} {6}').format(
        doc.from_shareholder or 'New Issue',
        doc.to_shareholder,
        doc.no_of_shares,
        flt(doc.rate_in_transaction_currency),
        doc.transaction_currency,
        flt(doc.total_amount_in_transaction_currency),
        doc.transaction_currency
    )
    
    # Set multi-currency flag
    je.multi_currency = 1 if doc.transaction_currency != company_currency else 0
    
    # Get cost center
    cost_center = doc.get('cost_center') or frappe.get_cached_value('Company', doc.company, 'cost_center')
    
    # --- Line 1: Debit Receiving Account (Asset) ---
    # New shareholder pays money to company
    je.append("accounts", {
        "account": doc.asset_account,
        "debit_in_account_currency": flt(doc.total_amount_in_transaction_currency),
        "credit_in_account_currency": 0,
        "account_currency": doc.transaction_currency,
        "exchange_rate": exchange_rate,
        
        "cost_center": cost_center,
        # "reference_type": "Share Transfer",
        # "reference_name": doc.name,
        "user_remark": _("Payment received for share transfer")
    })
    
    # --- Line 2: Credit Share Capital Account (Equity/Liability) ---
    # Company issues shares
    credit_entry = {
        "account": doc.equity_or_liability_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": flt(doc.total_amount_in_transaction_currency),
        "account_currency": doc.transaction_currency,
        "exchange_rate": exchange_rate,
        "party_type": "Shareholder",
        "party": doc.to_shareholder,
        "cost_center": cost_center,
        # "reference_type": "Share Transfer",
        # "reference_name": doc.name,
        "user_remark": _("Share capital for {0} shares").format(doc.no_of_shares)
    }
    
    # Only add party if from_shareholder exists (not for new issue)
    if doc.from_shareholder:
        credit_entry["party_type"] = "Shareholder"
        credit_entry["party"] = doc.from_shareholder
    
    je.append("accounts", credit_entry)
    
    # --- Save and submit JE ---
    try:
        je.flags.ignore_permissions = True
        je.insert()
        # je.submit()
        
        # --- Link JE to Share Transfer ---
        frappe.db.set_value("Share Transfer", doc.name, "custom_journal_entry", je.name)
        frappe.db.commit()
        
        return {
            'status': 'success',
            'journal_entry': je.name,
            'message': _('Journal Entry {0} created successfully').format(je.name)
        }
        
    except Exception as e:
        frappe.log_error(title='Share Transfer JE Creation Failed', message=str(e))
        frappe.throw(_('Failed to create Journal Entry: {0}').format(str(e)))


@frappe.whitelist()
def cancel_custom_journal_entry(docname):
    """
    Cancel the journal entry linked to a Share Transfer
    """
    doc = frappe.get_doc("Share Transfer", docname)
    
    if not doc.get('custom_journal_entry'):
        frappe.throw(_("No Journal Entry found for this Share Transfer"))
    
    try:
        je = frappe.get_doc('Journal Entry', doc.custom_journal_entry)
        
        if je.docstatus == 1:
            je.cancel()
            frappe.msgprint(_('Journal Entry {0} cancelled successfully').format(je.name))
            return {
                'status': 'success',
                'message': _('Journal Entry cancelled')
            }
        elif je.docstatus == 2:
            frappe.msgprint(_('Journal Entry is already cancelled'))
        else:
            frappe.msgprint(_('Journal Entry is not submitted'))
            
    except Exception as e:
        frappe.log_error(title='Share Transfer JE Cancellation Failed', message=str(e))
        frappe.throw(_('Failed to cancel Journal Entry: {0}').format(str(e)))

