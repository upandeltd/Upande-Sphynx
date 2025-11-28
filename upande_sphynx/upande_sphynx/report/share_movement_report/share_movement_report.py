import frappe
from frappe import _
from frappe.utils import fmt_money

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
         {'fieldname': 'date', 'label': _('Date'), 'fieldtype': 'Date', 'width': 120},
         {'fieldname': 'shareholder', 'label': _('Shareholder'), 'fieldtype': 'Link', 'options': 'Shareholder', 'width': 180},
       
        {'fieldname': 'document_type', 'label': _('Document Type'), 'fieldtype': 'Data', 'width': 140},
        {'fieldname': 'voucher_subtype', 'label': _('Voucher Subtype'), 'fieldtype': 'Data', 'width': 140},
        {'fieldname': 'document_name', 'label': _('Document Name'), 'fieldtype': 'Dynamic Link', 'options': 'document_type', 'width': 180},
        
        {'fieldname': 'debit_account', 'label': _('Debit Account'), 'fieldtype': 'Data', 'width': 180},
        {'fieldname': 'credit_account', 'label': _('Credit Account'), 'fieldtype': 'Data', 'width': 220},
        {'fieldname': 'amount', 'label': _('Amount'), 'fieldtype': 'Float', 'width': 130},
        {'fieldname': 'shares_units', 'label': _('Shares Issued'), 'fieldtype': 'Float', 'width': 110},
        # {'fieldname': 'movement_type', 'label': _('Movement Type'), 'fieldtype': 'Data', 'width': 130},
        {'fieldname': 'status', 'label': _('Status'), 'fieldtype': 'Data', 'width': 100},
        {'fieldname': 'remarks', 'label': _('Remarks/Description'), 'fieldtype': 'Data', 'width': 350},
    ]


def format_account(acc):
    """Return account as 'number - name' if available."""
    if not acc:
        return ''
    acc_info = frappe.db.get_value('GL Account', acc, ['account_number', 'account_name'], as_dict=True)
    if acc_info:
        if acc_info.account_number:
            return f"{acc_info.account_number} - {acc_info.account_name}"
        return acc_info.account_name
    return acc


def get_data(filters):
    data = []

    # -----------------------------------
    # SHARE TRANSFERS
    # -----------------------------------
    share_transfers = frappe.db.sql("""
        SELECT 
            st.date,
            st.name,
            st.to_shareholder AS shareholder,
            st.transfer_type,
            st.issue_type AS issue_type,
            st.equity_or_liability_account,
            st.asset_account,
            st.no_of_shares,
            st.custom_convertible_loan_amount AS amount,
            st.custom_journal_entry,
            st.docstatus
        FROM `tabShare Transfer` st
        WHERE st.docstatus IN (0, 1)
        ORDER BY st.to_shareholder, st.date DESC
    """, as_dict=1)

    for st in share_transfers:
        status_text = 'Draft' if st.docstatus == 0 else 'Submitted'

        # Determine subtype
        if st.transfer_type == "Issue":
            if st.issue_type == "Standard":
                voucher_subtype = "Issue"
            else:
                voucher_subtype = st.issue_type or "Issue"
        else:
            voucher_subtype = st.transfer_type or "N/A"

        # Accounts
        debit_account_name = format_account(st.asset_account)
        credit_account_name = format_account(st.equity_or_liability_account)

        # If there's a linked journal, show it in remarks
        je_subtype = None
        if st.custom_journal_entry:
            je_subtype = frappe.db.get_value("Journal Entry", st.custom_journal_entry, "voucher_type")

        remarks = f"{voucher_subtype} of {st.no_of_shares} shares"
        if st.custom_journal_entry:
            remarks += f" | Linked Journal: {st.custom_journal_entry}"
            if je_subtype:
                remarks += f" ({je_subtype})"

        data.append({
            'shareholder': st.shareholder,
            'date': st.date,
            'document_type': 'Share Transfer',
            'document_name': st.name,
            'voucher_subtype': voucher_subtype,
            'debit_account': debit_account_name,
            'credit_account': credit_account_name,
            'amount': st.amount or 0,
            'shares_units': st.no_of_shares,
            'movement_type': voucher_subtype,
            'status': status_text,
            'remarks': remarks
        })

    # -----------------------------------
    # JOURNAL ENTRIES (linked to Shareholders)
    # -----------------------------------
    journal_entries = frappe.db.sql("""
        SELECT 
            je.posting_date AS date,
            je.name,
            je.voucher_type,
            jea.party AS shareholder,
            jea.account,
            jea.against_account,
            jea.debit,
            jea.credit,
            jea.user_remark AS description,
            je.title,
            je.docstatus
        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
        WHERE je.docstatus IN (0, 1)
        AND jea.party_type = 'Shareholder'
        AND jea.party IS NOT NULL AND jea.party != ''
        ORDER BY jea.party, je.posting_date DESC
    """, as_dict=1)

    for je in journal_entries:
        status_text = 'Draft' if je.docstatus == 0 else 'Submitted'
        debit_account_name = format_account(je.account if je.debit > 0 else je.against_account)
        credit_account_name = format_account(je.account if je.credit > 0 else je.against_account)
        amount = je.debit or je.credit or 0
        remarks = je.description or je.title or 'No description'

        data.append({
            'shareholder': je.shareholder,
            'date': je.date,
            'document_type': 'Journal Entry',
            'document_name': je.name,
            'voucher_subtype': je.voucher_type or 'N/A',
            'debit_account': debit_account_name,
            'credit_account': credit_account_name,
            'amount': amount,
            'shares_units': 0,
            'movement_type': 'Journal Entry',
            'status': status_text,
            'remarks': remarks
        })

    # Sort & group by Shareholder then date
    data.sort(key=lambda x: (x['shareholder'] or '', x['date']), reverse=True)
    return data
