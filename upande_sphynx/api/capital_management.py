import frappe
from frappe import _
from frappe.utils import flt, get_datetime

# ============================================
# SHAREHOLDER TOTALS
# ============================================

def recalculate_shareholder_totals(shareholder_name):
	"""Recompute a Shareholder's Total Shares Held and Total Investment.

	Total Shares Held = shares received (to_shareholder) minus shares given up
	(from_shareholder, e.g. a buyback) across all submitted Share Movements.

	Total Investment = money paid in via submitted Share Movements (excluding
	Share Buyback, which returns capital rather than investing it) plus any
	currently active (unconverted) Convertible Loan Note principal, so a loan
	counts once as principal while active and is not double-counted after it
	converts into a Share Movement.
	"""
	if not shareholder_name:
		return

	totals = frappe.db.sql("""
		SELECT
			SUM(CASE WHEN to_shareholder = %(shareholder)s THEN number_of_shares ELSE 0 END)
			- SUM(CASE WHEN from_shareholder = %(shareholder)s THEN number_of_shares ELSE 0 END) AS shares_held,
			SUM(CASE WHEN to_shareholder = %(shareholder)s AND movement_type != 'Share Buyback'
				THEN total_amount_base_currency ELSE 0 END) AS shares_investment
		FROM `tabShare Movement`
		WHERE docstatus = 1
		AND (to_shareholder = %(shareholder)s OR from_shareholder = %(shareholder)s)
	""", {"shareholder": shareholder_name}, as_dict=True)[0]

	active_cln_principal = flt(frappe.db.get_value("Shareholder", shareholder_name, "custom_total_cln_amount"))

	frappe.db.set_value("Shareholder", shareholder_name, {
		"custom_total_shares_held": flt(totals.shares_held),
		"custom_total_investment": flt(totals.shares_investment) + active_cln_principal,
	}, update_modified=False)


@frappe.whitelist()
def recompute_shareholder_totals(shareholder_name=None):
	"""Recompute Total Shares Held / Total Investment for one Shareholder, or
	every Shareholder if none is given. Use this once to backfill existing
	records, since those fields were never populated before this was wired up."""
	names = [shareholder_name] if shareholder_name else frappe.get_all("Shareholder", pluck="name")
	for name in names:
		recalculate_shareholder_totals(name)
	frappe.db.commit()
	return {"recalculated": len(names)}


# ============================================
# SHARE AGREEMENT FUNCTIONS
# ============================================

@frappe.whitelist()
def issue_shares_from_agreement(share_agreement_name):
    """Create Share Movement from Share Agreement (NO Journal Entry here)"""
    agreement = frappe.get_doc("Share Agreement", share_agreement_name)
    
    if agreement.docstatus != 1:
        frappe.throw(_("Share Agreement must be submitted first"))
    
    if agreement.share_movement_ref:
        frappe.throw(_("Shares already issued: {0}").format(agreement.share_movement_ref))
    
    if not agreement.company:
        frappe.throw(_("Please specify Company"))
    
    # Get company shareholder
    company_shareholder = frappe.db.get_value("Shareholder", {"company": agreement.company}, "name")
    
    if not company_shareholder:
        frappe.throw(_("Company shareholder not found. Please create a Shareholder record for the company"))
    
    # Get company base currency
    company_currency = frappe.get_cached_value("Company", agreement.company, "default_currency")
    transaction_currency = agreement.transaction_currency or "USD"
    
    # Calculate amounts
    total_amount = agreement.number_of_shares * agreement.rate_per_share
    share_capital = agreement.number_of_shares * agreement.par_value_per_share
    share_premium = total_amount - share_capital
    
    # Get exchange rate
    exchange_rate = agreement.exchange_rate or 1.0
    if not agreement.exchange_rate and transaction_currency != company_currency:
        exchange_rate = get_exchange_rate(transaction_currency, company_currency, agreement.agreement_date)
    
    # Create Share Movement (without Journal Entry)
    sm = frappe.get_doc({
        "doctype": "Share Movement",
        "transaction_date": agreement.agreement_date,
        "movement_type": "Equity Capital Injection",
        "company": agreement.company,
        "from_shareholder": company_shareholder,
        "to_shareholder": agreement.shareholder,
        "share_class": agreement.share_type,
        "number_of_shares": agreement.number_of_shares,
        "par_value_per_share": agreement.par_value_per_share,
        "par_value_currency": transaction_currency,
        "price_per_share": agreement.rate_per_share,
        "transaction_currency": transaction_currency,
        "total_amount": total_amount,
        "exchange_rate": exchange_rate,
        "base_currency": company_currency,
        "total_amount_base_currency": total_amount * exchange_rate,
        "share_capital_account": agreement.share_capital_account,
        "share_premium_account": agreement.share_premium_account,
        "share_capital_amount": share_capital,
        "share_premium_amount": share_premium,
        "bank_account": agreement.bank_account,
        "payment_date": agreement.payment_date,
        "source_document_type": "Share Agreement",
        "source_document_name": agreement.name,
        "share_agreement_type": agreement.agreement_type,
        "remarks": "Shares issued as per Share Agreement {0}".format(agreement.name),
        "is_opening_entry": agreement.is_opening_entry or "No",
        "auto_create_journal_entry": 0 if agreement.is_opening_entry == "Yes" else 1
    })
    
    sm.insert(ignore_permissions=True)
    sm.save()
    
    # Update Share Agreement using db_set (works for submitted documents)
    frappe.db.set_value("Share Agreement", agreement.name, {
        "share_movement_ref": sm.name,
        "status": "Shares Issued"
    })
    
    frappe.db.commit()
    
    frappe.msgprint(_("Share Movement {0} created successfully. Please create Journal Entry from Share Movement to record payment.").format(sm.name))

    return sm.name


@frappe.whitelist()
def cancel_share_agreement(share_agreement_name):
    """Cancel a submitted Share Agreement and its linked Share Movement/Journal Entry.

    The cascade (cancelling the linked Share Movement and Journal Entry) is handled
    by ShareAgreement.on_cancel() - this just triggers the standard cancel flow.
    """
    agreement = frappe.get_doc("Share Agreement", share_agreement_name)

    if agreement.docstatus != 1:
        frappe.throw(_("Only a submitted Share Agreement can be cancelled"))

    agreement.cancel()

    return agreement.name


@frappe.whitelist()
def delete_share_agreement(share_agreement_name):
    """Permanently delete a cancelled Share Agreement and its linked documents.

    The cascade (deleting the linked, already-cancelled Share Movement/Journal Entry)
    is handled by ShareAgreement.on_trash() - this just triggers the standard delete flow.
    """
    agreement = frappe.get_doc("Share Agreement", share_agreement_name)

    if agreement.docstatus != 2:
        frappe.throw(_("Only a cancelled Share Agreement can be deleted"))

    frappe.delete_doc("Share Agreement", share_agreement_name, ignore_permissions=True)

    return share_agreement_name


# ============================================
# SHARE MOVEMENT FUNCTIONS
# ============================================

@frappe.whitelist()
def create_journal_entry_from_share_movement(share_movement_name):
    """Create Journal Entry from Share Movement to record payment
    
    ACCOUNTING LOGIC:
    For Share Issuance (money coming in):
        Dr: Bank Account (Asset increases)
            Cr: Share Capital Account (Equity increases)
            Cr: Share Premium Account (if premium > 0) (Equity increases)
    """
    sm = frappe.get_doc("Share Movement", share_movement_name)
    
    if sm.docstatus != 1:
        frappe.throw(_("Share Movement must be submitted first"))

    if sm.is_opening_entry == "Yes":
        frappe.throw(_(
            "This is an Opening Entry — no Journal Entry is needed. "
            "The opening balance is already captured in your opening balance accounts."
        ))

    if sm.journal_entry_ref:
        frappe.throw(_("Journal Entry already created: {0}").format(sm.journal_entry_ref))

    if not sm.bank_account:
        frappe.throw(_("Please specify Bank Account before creating Journal Entry"))
    
    # Get bank account GL account
    bank_account_doc = frappe.get_doc("Bank Account", sm.bank_account)
    bank_gl_account = bank_account_doc.account
    
    # Determine debit/credit based on movement type
    is_inflow = sm.movement_type in [
        "Equity Capital Injection",
        "Share Purchase",
        "Loan Equity Injection"
    ]
    
    accounts = []
    
    if is_inflow:
        # Money coming in
        # Dr: Bank Account (money received)
        accounts.append({
            "account": bank_gl_account,
            "debit_in_account_currency": sm.total_amount,
            "account_currency": sm.transaction_currency,
            "exchange_rate": sm.exchange_rate,
            # "reference_type": "Share Movement",
            # "reference_name": sm.name,
            "company": sm.company,
            "against_account": ", ".join(filter(None, [sm.share_capital_account, sm.share_premium_account if sm.share_premium_amount > 0 else None]))
        })
        
        # Cr: Share Capital (par value portion)
        accounts.append({
            "account": sm.share_capital_account,
            "credit_in_account_currency": sm.share_capital_amount,
            "account_currency": sm.transaction_currency,
            "exchange_rate": sm.exchange_rate,
            "company": sm.company,
            "against_account": bank_gl_account
        })
        
        # Cr: Share Premium (premium portion, if any)
        if sm.share_premium_amount > 0:
            accounts.append({
                "account": sm.share_premium_account,
                "credit_in_account_currency": sm.share_premium_amount,
                "account_currency": sm.transaction_currency,
                "exchange_rate": sm.exchange_rate,
                "company": sm.company,
                "against_account": bank_gl_account
            })
        
        user_remark = "Payment received for Share Movement {0} - {1} shares to {2}".format(
            sm.name, sm.number_of_shares, sm.to_shareholder
        )
    
    elif sm.movement_type == "Share Buyback":
        # Money going out
        # Cr: Bank Account (money paid out)
        accounts.append({
            "account": bank_gl_account,
            "credit_in_account_currency": sm.total_amount,
            "account_currency": sm.transaction_currency,
            "exchange_rate": sm.exchange_rate,
            # "reference_type": "Share Movement",
            # "reference_name": sm.name,
            "company": sm.company,
            "against_account": ", ".join(filter(None, [sm.share_capital_account, sm.share_premium_account if sm.share_premium_amount > 0 else None]))
        })
        
        # Dr: Share Capital (reducing equity)
        accounts.append({
            "account": sm.share_capital_account,
            "debit_in_account_currency": sm.share_capital_amount,
            "account_currency": sm.transaction_currency,
            "exchange_rate": sm.exchange_rate,
            "company": sm.company,
            "against_account": bank_gl_account
        })
        
        # Dr: Share Premium (if any)
        if sm.share_premium_amount > 0:
            accounts.append({
                "account": sm.share_premium_account,
                "debit_in_account_currency": sm.share_premium_amount,
                "account_currency": sm.transaction_currency,
                "exchange_rate": sm.exchange_rate,
                "company": sm.company,
                "against_account": bank_gl_account
            })
        
        user_remark = "Payment for Share Buyback {0} - {1} shares from {2}".format(
            sm.name, sm.number_of_shares, sm.from_shareholder
        )
    
    else:
        frappe.throw(_("Journal Entry creation not applicable for movement type: {0}").format(sm.movement_type))
    
    # Create Journal Entry
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": sm.payment_date or sm.transaction_date,
        "company": sm.company,
        "multi_currency": 1 if sm.transaction_currency != sm.base_currency else 0,
        "user_remark": user_remark,
        "accounts": accounts
    })
    
    je.insert(ignore_permissions=True)
    je.submit()
    
    # Update Share Movement using db_set
    frappe.db.set_value("Share Movement", sm.name,
                        {"journal_entry_ref": je.name,
                         "status": "Issued"
                        })

    frappe.db.commit()
    
    frappe.msgprint(_("Journal Entry {0} created successfully").format(je.name))

    return je.name


@frappe.whitelist()
def cancel_share_movement(share_movement_name):
    """Cancel a submitted Share Movement and its linked Journal Entry.

    The cascade (cancelling the linked Journal Entry and resetting the source
    Share Agreement) is handled by ShareMovement.on_cancel() - this just triggers
    the standard cancel flow.
    """
    sm = frappe.get_doc("Share Movement", share_movement_name)

    if sm.docstatus != 1:
        frappe.throw(_("Only a submitted Share Movement can be cancelled"))

    sm.cancel()

    return sm.name


@frappe.whitelist()
def delete_share_movement(share_movement_name):
    """Permanently delete a cancelled Share Movement and its linked Journal Entry.

    The cascade (deleting the already-cancelled Journal Entry) is handled by
    ShareMovement.on_trash() - this just triggers the standard delete flow.
    """
    sm = frappe.get_doc("Share Movement", share_movement_name)

    if sm.docstatus != 2:
        frappe.throw(_("Only a cancelled Share Movement can be deleted"))

    frappe.delete_doc("Share Movement", share_movement_name, ignore_permissions=True)

    return share_movement_name


# ============================================
# CONVERTIBLE LOAN NOTE FUNCTIONS
# ============================================

@frappe.whitelist()
def record_cln_disbursement(cln_name):
    """Create Journal Entry to record CLN loan disbursement
    
    ACCOUNTING LOGIC:
    Loan Disbursement (company receiving loan):
        Dr: Bank Account (Asset increases - money received)
        Cr: Loan Liability Account (Liability increases - owe money)
    """
    cln = frappe.get_doc("Convertible Loan Note", cln_name)
    
    if cln.docstatus != 1:
        frappe.throw(_("Convertible Loan Note must be submitted first"))
    
    if cln.disbursement_journal_entry_ref:
        frappe.throw(_("Disbursement already recorded: {0}").format(cln.disbursement_journal_entry_ref))

    if cln.is_opening_entry == "Yes":
        # The loan balance already exists in the opening balance accounts —
        # just activate the loan, no Journal Entry.
        frappe.db.set_value("Convertible Loan Note", cln.name, "status", "Active")

        shareholder = frappe.get_doc("Shareholder", cln.lender)
        shareholder.custom_has_convertible_loans = 1
        shareholder.custom_total_cln_amount = frappe.db.sql("""
            SELECT SUM(principal_amount)
            FROM `tabConvertible Loan Note`
            WHERE lender = %s AND status = 'Active' AND docstatus = 1
        """, cln.lender)[0][0] or 0
        shareholder.save(ignore_permissions=True)
        recalculate_shareholder_totals(cln.lender)

        frappe.db.commit()

        frappe.msgprint(_("Opening Entry — CLN marked Active. No Journal Entry was created, since the balance is already in your opening balance accounts."))

        return None

    if not cln.bank_account:
        frappe.throw(_("Please specify Bank Account before recording disbursement"))
    
    if not cln.company:
        frappe.throw(_("Please specify Company"))
    
    if not cln.loan_liability_account:
        frappe.throw(_("Please specify Loan Liability Account"))
    
    # Get bank account details
    bank_account_doc = frappe.get_doc("Bank Account", cln.bank_account)
    bank_gl_account = bank_account_doc.account
    
    if not bank_gl_account:
        frappe.throw(_("Bank Account {0} does not have a linked GL Account").format(cln.bank_account))
    
    # Get currencies
    loan_currency = cln.loan_currency or "USD"
    company_currency = frappe.get_cached_value("Company", cln.company, "default_currency")
    
    # Get exchange rate
    exchange_rate = cln.exchange_rate or 1.0
    if not cln.exchange_rate and loan_currency != company_currency:
        exchange_rate = get_exchange_rate(loan_currency, company_currency, cln.issue_date)
    
    # Create Journal Entry
    # Dr: Bank (receiving money)
    # Cr: Loan Liability (owing money)
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": cln.issue_date,
        "company": cln.company,
        "multi_currency": 1 if loan_currency != company_currency else 0,
        "user_remark": "Convertible Loan Note {0} disbursement from {1}".format(
            cln.name, cln.lender
        ),
        "accounts": [
            {
                "account": bank_gl_account,
                "debit_in_account_currency": cln.principal_amount,
                "account_currency": loan_currency,
                "exchange_rate": exchange_rate,
                # "reference_type": "Convertible Loan Note",
                # "reference_name": cln.name,
                "company": cln.company,
                "against_account": cln.loan_liability_account
            },
            {
                "account": cln.loan_liability_account,
                "credit_in_account_currency": cln.principal_amount,
                "account_currency": loan_currency,
                "exchange_rate": exchange_rate,
                "party_type": "Shareholder",
                "party": cln.lender,
                "company": cln.company,
                "against_account": bank_gl_account
            }
        ]
    })
    
    je.insert(ignore_permissions=True)
    je.submit()
    
    # Update CLN using db_set
    frappe.db.set_value("Convertible Loan Note", cln.name, {
        "disbursement_journal_entry_ref": je.name,
        "status": "Active"
    })
    
    # Update Shareholder
    shareholder = frappe.get_doc("Shareholder", cln.lender)
    shareholder.custom_has_convertible_loans = 1
    shareholder.custom_total_cln_amount = frappe.db.sql("""
        SELECT SUM(principal_amount)
        FROM `tabConvertible Loan Note`
        WHERE lender = %s AND status = 'Active' AND docstatus = 1
    """, cln.lender)[0][0] or 0
    shareholder.save(ignore_permissions=True)
    recalculate_shareholder_totals(cln.lender)

    frappe.db.commit()

    frappe.msgprint(_("Journal Entry {0} created successfully for CLN disbursement").format(je.name))
    
    return je.name

import frappe
from frappe import _
from frappe.utils import flt, getdate

@frappe.whitelist()
def accrue_cln_interest(cln_name, accrual_date=None, exchange_rate=None):
    """
    Accrue interest for Convertible Loan Note with user-specified date and exchange rate
    Now with interest accrual history tracking
    
    Parameters:
    - cln_name: Name of the Convertible Loan Note
    - accrual_date: Date to post the interest accrual (defaults to today if not provided)
    - exchange_rate: Exchange rate to use for multi-currency (optional)
    """
    cln = frappe.get_doc("Convertible Loan Note", cln_name)
    
    if cln.docstatus != 1:
        frappe.throw(_("Convertible Loan Note must be submitted first"))
    
    if cln.status != "Active":
        frappe.throw(_("CLN must be in Active status to accrue interest"))
    
    if not cln.company:
        frappe.throw(_("Please specify Company"))
    
    # Use user-provided accrual date or default to today
    end_date = accrual_date or frappe.utils.today()
    
    # Validate accrual date
    end_datetime = getdate(end_date)
    
    # Calculate interest from last accrual date or issue date
    start_date = cln.last_interest_accrual_date or cln.issue_date
    start_datetime = getdate(start_date)
    
    if start_datetime >= end_datetime:
        frappe.throw(_("Accrual date must be after the last accrual date ({0})").format(start_date))
    
    # Calculate days
    days_difference = (end_datetime - start_datetime).days
    
    # Calculate interest in loan currency
    if cln.interest_calculation_method == "Simple":
        interest = (cln.principal_amount * cln.interest_rate * days_difference) / (100 * 365)
    else:
        # Compound interest - yearly compounding
        years = days_difference / 365
        interest = cln.principal_amount * ((1 + cln.interest_rate/100) ** years - 1)
    
    interest = flt(interest, 2)  # Round to 2 decimal places
    
    if interest <= 0:
        frappe.throw(_("Calculated interest is zero or negative"))
    
    # Get currencies
    loan_currency = cln.loan_currency or "USD"
    company_currency = frappe.get_cached_value("Company", cln.company, "default_currency")
    
    # Use user-provided exchange rate or get from CLN or fetch current rate
    if exchange_rate:
        final_exchange_rate = flt(exchange_rate, 6)
    elif cln.exchange_rate:
        final_exchange_rate = flt(cln.exchange_rate, 6)
    elif loan_currency != company_currency:
        final_exchange_rate = flt(get_exchange_rate(loan_currency, company_currency, end_date), 6)
    else:
        final_exchange_rate = 1.0
    
    # Calculate interest in base currency
    interest_base = flt(interest * final_exchange_rate, 2)
    
    # Determine interest payable account
    interest_payable_account = cln.interest_payable_account or cln.loan_liability_account
    
    # Get account currencies
    interest_expense_account_currency = frappe.get_cached_value("Account", cln.interest_expense_account, "account_currency")
    interest_payable_account_currency = frappe.get_cached_value("Account", interest_payable_account, "account_currency")
    
    # Build accounts list
    accounts = []
    
    # Dr: Interest Expense (increasing expense)
    if interest_expense_account_currency == company_currency or not interest_expense_account_currency:
        # Interest Expense in company currency
        accounts.append({
            "account": cln.interest_expense_account,
            "debit_in_account_currency": interest_base,
            "account_currency": company_currency,
            "exchange_rate": 1.0,
            # "reference_type": "Convertible Loan Note",
            # "reference_name": cln.name,
            "company": cln.company,
            "against_account": interest_payable_account
        })
    else:
        # Interest Expense in loan currency (rare case)
        accounts.append({
            "account": cln.interest_expense_account,
            "debit_in_account_currency": interest,
            "account_currency": loan_currency,
            "exchange_rate": final_exchange_rate,
            # "reference_type": "Convertible Loan Note",
            # "reference_name": cln.name,
            "company": cln.company,
            "against_account": interest_payable_account
        })
    
    # Cr: Interest Payable/Loan Liability (increasing liability)
    if interest_payable_account_currency == loan_currency or (loan_currency != company_currency):
        # Interest Payable in loan currency (most common)
        accounts.append({
            "account": interest_payable_account,
            "credit_in_account_currency": interest,
            "account_currency": loan_currency,
            "exchange_rate": final_exchange_rate,
            "party_type": "Shareholder",
            "party": cln.lender,
            # "reference_type": "Convertible Loan Note",
            # "reference_name": cln.name,
            "company": cln.company,
            "against_account": cln.interest_expense_account
        })
    else:
        # Interest Payable in company currency
        accounts.append({
            "account": interest_payable_account,
            "credit_in_account_currency": interest_base,
            "account_currency": company_currency,
            "exchange_rate": 1.0,
            "party_type": "Shareholder",
            "party": cln.lender,
            # "reference_type": "Convertible Loan Note",
            # "reference_name": cln.name,
            "company": cln.company,
            "against_account": cln.interest_expense_account
        })
    
    # Create Journal Entry
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": end_date,
        "company": cln.company,
        "multi_currency": 1 if loan_currency != company_currency else 0,
        "user_remark": "Interest accrual for CLN {0} from {1} to {2} ({3} days at {4}%)".format(
            cln.name, start_date, end_date, days_difference, cln.interest_rate
        ),
        "accounts": accounts
    })
    
    je.insert(ignore_permissions=True)
    je.submit()
    
    # Update CLN with new accrued interest
    new_total_accrued = flt((cln.accrued_interest or 0) + interest, 2)
    
    # Get the CLN doc again to add child table row
    cln_doc = frappe.get_doc("Convertible Loan Note", cln.name)
    cln_doc.accrued_interest = new_total_accrued
    cln_doc.last_interest_accrual_date = end_date
    
    # Add entry to interest accrual history child table
    cln_doc.append("interest_accruals", {
        "accrual_date": end_date,
        "from_date": start_date,
        "to_date": end_date,
        "days": days_difference,
        "interest_amount": interest,
        "exchange_rate": final_exchange_rate,
        "interest_amount_base": interest_base,
        "journal_entry": je.name,
        "cumulative_interest": new_total_accrued,
        "currency": loan_currency,
        "remarks": "Interest rate: {0}%, Method: {1}".format(
            cln.interest_rate,
            cln.interest_calculation_method or "Simple"
        )
    })
    
    # Calculate total from table for verification
    total_from_table = sum([flt(row.interest_amount) for row in cln_doc.interest_accruals])
    cln_doc.total_accrued_from_table = total_from_table
    
    # Add dynamic link (if dynamic links are set up)
    try:
        cln_doc.add_link("Journal Entry", je.name, autosave=False)
    except:
        # If dynamic links not set up, continue
        pass
    
    cln_doc.flags.ignore_validate = True
    cln_doc.flags.ignore_mandatory = True
    cln_doc.save(ignore_permissions=True)
    
    frappe.db.commit()
    
    frappe.msgprint(_("""Interest accrued successfully!
        <br><br>
        <b>Period:</b> {0} to {1} ({2} days)<br>
        <b>Interest Amount ({3}):</b> {4}<br>
        <b>Interest Amount ({5}):</b> {6}<br>
        <b>Exchange Rate Used:</b> {7}<br>
        <b>Journal Entry:</b> {8}<br>
        <b>Total Accrued Interest:</b> {9}<br>
        <b>Number of Accruals:</b> {10}
    """).format(
        start_date, 
        end_date,
        days_difference,
        loan_currency,
        frappe.utils.fmt_money(interest, currency=loan_currency),
        company_currency,
        frappe.utils.fmt_money(interest_base, currency=company_currency),
        final_exchange_rate,
        je.name,
        frappe.utils.fmt_money(new_total_accrued, currency=loan_currency),
        len(cln_doc.interest_accruals)
    ))
    
    return {
        "journal_entry": je.name,
        "interest_amount": interest,
        "interest_amount_base": interest_base,
        "total_accrued": new_total_accrued,
        "accrual_date": end_date,
        "exchange_rate_used": final_exchange_rate,
        "days_accrued": days_difference,
        "accrual_count": len(cln_doc.interest_accruals)
    }


@frappe.whitelist()
def get_cln_outstanding_balance(cln_name):
    """Return what's still owed on a CLN after any prior repayment installments."""
    cln = frappe.get_doc("Convertible Loan Note", cln_name)
    paid_principal = sum(flt(row.principal_paid) for row in cln.repayments)
    paid_interest = sum(flt(row.interest_paid) for row in cln.repayments)
    return {
        "outstanding_principal": flt(cln.principal_amount) - paid_principal,
        "outstanding_interest": flt(cln.accrued_interest) - paid_interest,
    }


@frappe.whitelist()
def record_cln_repayment(cln_name, repayment_date=None, principal_amount=None, interest_amount=None,
                          penalty_amount=None, exchange_rate=None):
    """Repay a Convertible Loan Note in cash instead of converting it to shares.
    Supports partial, installment-based repayment — call this once per
    installment; each call records what was paid *this time*, not
    necessarily the full outstanding balance. Leave principal_amount /
    interest_amount unset to default to paying off everything outstanding
    in one go.

    ACCOUNTING LOGIC (per installment):
    Loan Repayment (company paying back the lender):
        Dr: Loan Liability Account (this installment's principal portion)
        Dr: Interest Payable Account (this installment's interest portion, if any)
        Dr: Interest Expense Account (if an early repayment penalty applies)
            Cr: Bank Account (money paid out this time)
    """
    cln = frappe.get_doc("Convertible Loan Note", cln_name)

    if cln.docstatus != 1:
        frappe.throw(_("Convertible Loan Note must be submitted first"))

    if cln.status != "Active":
        frappe.throw(_("CLN must be in Active status to record repayment"))

    if not cln.bank_account:
        frappe.throw(_("Please specify Bank Account before recording repayment"))

    if not cln.company:
        frappe.throw(_("Please specify Company"))

    repayment_date = repayment_date or frappe.utils.today()
    penalty_amount = flt(penalty_amount)

    if penalty_amount and not cln.early_repayment_allowed:
        frappe.throw(_("Early Repayment Penalty was provided, but this CLN does not have 'Early Repayment Allowed' checked"))

    if penalty_amount and not cln.interest_expense_account:
        frappe.throw(_("Please specify Interest Expense Account to record the early repayment penalty"))

    balance = get_cln_outstanding_balance(cln_name)
    outstanding_principal = flt(balance["outstanding_principal"])
    outstanding_interest = flt(balance["outstanding_interest"])

    # Default to paying off everything outstanding, if this installment's
    # amounts weren't specified — preserves "just repay it" as the simple case.
    principal_amount = outstanding_principal if principal_amount is None else flt(principal_amount)
    interest_amount = outstanding_interest if interest_amount is None else flt(interest_amount)

    if principal_amount < 0 or interest_amount < 0:
        frappe.throw(_("Principal and interest amounts can't be negative"))

    if principal_amount - outstanding_principal > 0.01:
        frappe.throw(_("Principal being repaid ({0}) is more than what's outstanding ({1})").format(
            principal_amount, outstanding_principal))

    if interest_amount - outstanding_interest > 0.01:
        frappe.throw(_("Interest being repaid ({0}) is more than what's outstanding ({1})").format(
            interest_amount, outstanding_interest))

    if principal_amount <= 0 and interest_amount <= 0:
        frappe.throw(_("Nothing to repay — this loan's outstanding balance is already zero"))

    bank_account_doc = frappe.get_doc("Bank Account", cln.bank_account)
    bank_gl_account = bank_account_doc.account

    if not bank_gl_account:
        frappe.throw(_("Bank Account {0} does not have a linked GL Account").format(cln.bank_account))

    loan_currency = cln.loan_currency or "USD"
    company_currency = frappe.get_cached_value("Company", cln.company, "default_currency")

    if exchange_rate:
        final_exchange_rate = flt(exchange_rate)
    elif cln.exchange_rate:
        final_exchange_rate = flt(cln.exchange_rate)
    elif loan_currency != company_currency:
        final_exchange_rate = get_exchange_rate(loan_currency, company_currency, repayment_date)
    else:
        final_exchange_rate = 1.0

    interest_payable_account = cln.interest_payable_account or cln.loan_liability_account
    this_installment_total = principal_amount + interest_amount + penalty_amount

    accounts = []

    if principal_amount > 0:
        # Dr: Loan Liability (this installment's principal)
        accounts.append({
            "account": cln.loan_liability_account,
            "debit_in_account_currency": principal_amount,
            "account_currency": loan_currency,
            "exchange_rate": final_exchange_rate,
            "party_type": "Shareholder",
            "party": cln.lender,
            "company": cln.company,
            "against_account": bank_gl_account
        })

    if interest_amount > 0:
        # Dr: Interest Payable (this installment's interest)
        accounts.append({
            "account": interest_payable_account,
            "debit_in_account_currency": interest_amount,
            "account_currency": loan_currency,
            "exchange_rate": final_exchange_rate,
            "party_type": "Shareholder",
            "party": cln.lender,
            "company": cln.company,
            "against_account": bank_gl_account
        })

    if penalty_amount > 0:
        # Dr: Interest Expense (cost of repaying early)
        accounts.append({
            "account": cln.interest_expense_account,
            "debit_in_account_currency": penalty_amount,
            "account_currency": loan_currency,
            "exchange_rate": final_exchange_rate,
            "company": cln.company,
            "against_account": bank_gl_account
        })

    accounts.append({
        # Cr: Bank (money paid out this installment)
        "account": bank_gl_account,
        "credit_in_account_currency": this_installment_total,
        "account_currency": loan_currency,
        "exchange_rate": final_exchange_rate,
        "company": cln.company,
        "against_account": cln.loan_liability_account
    })

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": repayment_date,
        "company": cln.company,
        "multi_currency": 1 if loan_currency != company_currency else 0,
        "user_remark": "Repayment installment for Convertible Loan Note {0} to {1}".format(cln.name, cln.lender),
        "accounts": accounts
    })

    je.insert(ignore_permissions=True)
    je.submit()

    remaining_principal = flt(outstanding_principal - principal_amount, 2)
    remaining_interest = flt(outstanding_interest - interest_amount, 2)
    fully_repaid = remaining_principal <= 0.01 and remaining_interest <= 0.01

    # Reload to append to the child table and update summary fields
    cln_doc = frappe.get_doc("Convertible Loan Note", cln.name)
    cln_doc.append("repayments", {
        "repayment_date": repayment_date,
        "principal_paid": principal_amount,
        "interest_paid": interest_amount,
        "penalty_paid": penalty_amount,
        "exchange_rate": final_exchange_rate,
        "journal_entry": je.name,
        "remaining_principal": max(remaining_principal, 0),
        "remaining_interest": max(remaining_interest, 0),
        "currency": loan_currency,
        "remarks": "Fully repaid" if fully_repaid else "Partial repayment installment"
    })
    cln_doc.total_repaid = flt((cln_doc.total_repaid or 0) + this_installment_total, 2)

    if fully_repaid:
        cln_doc.status = "Repaid"
        cln_doc.repayment_date = repayment_date

    cln_doc.flags.ignore_validate = True
    cln_doc.flags.ignore_mandatory = True
    cln_doc.save(ignore_permissions=True)

    # Update Shareholder — only drops out of the "Active" total once fully repaid
    shareholder = frappe.get_doc("Shareholder", cln.lender)
    shareholder.custom_total_cln_amount = frappe.db.sql("""
        SELECT SUM(principal_amount)
        FROM `tabConvertible Loan Note`
        WHERE lender = %s AND status = 'Active' AND docstatus = 1
    """, cln.lender)[0][0] or 0
    shareholder.custom_has_convertible_loans = 1 if shareholder.custom_total_cln_amount > 0 else 0
    shareholder.save(ignore_permissions=True)
    recalculate_shareholder_totals(cln.lender)

    frappe.db.commit()

    if fully_repaid:
        frappe.msgprint(_("Convertible Loan Note {0} fully repaid. Journal Entry: {1}").format(cln.name, je.name))
    else:
        frappe.msgprint(_("Repayment installment recorded for {0}. Journal Entry: {1}. Remaining: {2} principal, {3} interest.").format(
            cln.name, je.name, remaining_principal, remaining_interest))

    return {
        "journal_entry": je.name,
        "repayment_date": repayment_date,
        "principal_paid": principal_amount,
        "interest_paid": interest_amount,
        "penalty_amount": penalty_amount,
        "installment_total": this_installment_total,
        "remaining_principal": max(remaining_principal, 0),
        "remaining_interest": max(remaining_interest, 0),
        "fully_repaid": fully_repaid
    }


def get_exchange_rate(from_currency, to_currency, transaction_date):
    """Get exchange rate between two currencies"""
    if from_currency == to_currency:
        return 1.0
    
    from erpnext.setup.utils import get_exchange_rate as erpnext_exchange_rate
    
    try:
        exchange_rate = erpnext_exchange_rate(from_currency, to_currency, transaction_date)
        return flt(exchange_rate, 6)
    except:
        frappe.throw(_("Exchange rate not found for {0} to {1} on {2}. Please provide exchange_rate parameter or create a Currency Exchange record").format(
            from_currency, to_currency, transaction_date
        ))

@frappe.whitelist()
def convert_cln_to_shares(cln_name, next_round_price=None, fully_diluted_shares=None):
    """Convert Convertible Loan Note to shares - Creates both JE and Share Movement
    
    ACCOUNTING LOGIC:
    Conversion (settling liability with equity):
        Dr: Loan Liability Account (Liability decreases - debt cleared)
        Dr: Interest Payable Account (if any) (Liability decreases)
            Cr: Share Capital Account (Equity increases)
            Cr: Share Premium Account (if premium > 0) (Equity increases)
    """
    cln = frappe.get_doc("Convertible Loan Note", cln_name)
    
    if cln.docstatus != 1:
        frappe.throw(_("Convertible Loan Note must be submitted first"))
    
    if cln.status != "Active":
        frappe.throw(_("CLN must be in Active status to convert"))
    
    if cln.share_transfer_ref:
        frappe.throw(_("CLN already converted: {0}").format(cln.share_transfer_ref))
    
    if not cln.company:
        frappe.throw(_("Please specify Company"))
    
    # Calculate total amount to convert
    total_amount = cln.principal_amount + (cln.accrued_interest or 0)
    
    # Calculate conversion price
    conversion_price = calculate_conversion_price(cln, next_round_price, fully_diluted_shares)
    
    # Calculate number of shares
    num_shares = int(total_amount / conversion_price)
    
    if num_shares <= 0:
        frappe.throw(_("Calculated shares is zero or negative"))
    
    # Calculate accounting amounts
    share_capital_amount = num_shares * cln.par_value_per_share
    share_premium_amount = total_amount - share_capital_amount
    
    company_currency = frappe.get_cached_value("Company", cln.company, "default_currency")
    loan_currency = cln.loan_currency or "USD"
    exchange_rate = cln.exchange_rate or 1.0
    
    # Step 1: Create Journal Entry for conversion
    je = create_cln_conversion_journal_entry(
        cln, 
        total_amount, 
        share_capital_amount, 
        share_premium_amount,
        loan_currency,
        company_currency,
        exchange_rate
    )
    
    # Step 2: Get company shareholder
    company_shareholder = frappe.db.get_value("Shareholder", {"company": cln.company}, "name")
    
    if not company_shareholder:
        frappe.throw(_("Company shareholder not found"))
    
    # Step 3: Create Share Movement
    sm = frappe.get_doc({
        "doctype": "Share Movement",
        "transaction_date": frappe.utils.today(),
        "movement_type": "Loan Equity Injection",
        "company": cln.company,
        "from_shareholder": company_shareholder,
        "to_shareholder": cln.lender,
        "share_class": cln.conversion_share_type,
        "number_of_shares": num_shares,
        "par_value_per_share": cln.par_value_per_share,
        "par_value_currency": loan_currency,
        "price_per_share": conversion_price,
        "transaction_currency": loan_currency,
        "total_amount": total_amount,
        "exchange_rate": exchange_rate,
        "base_currency": company_currency,
        "total_amount_base_currency": total_amount * exchange_rate,
        "share_capital_account": cln.share_capital_account,
        "share_premium_account": cln.share_premium_account,
        "share_capital_amount": share_capital_amount,
        "share_premium_amount": share_premium_amount,
        "journal_entry_ref": je.name,
        "source_document_type": "Convertible Loan Note",
        "source_document_name": cln.name,
        "conversion_details": "Discount: {0}%, Valuation Cap: {1}, Conversion Price: {2}".format(
            cln.conversion_discount_rate or 0,
            frappe.utils.fmt_money(cln.valuation_cap) if cln.valuation_cap else "N/A",
            frappe.utils.fmt_money(conversion_price)
        ),
        "remarks": "Converted from Convertible Loan Note {0}".format(cln.name)
    })
    
    sm.insert(ignore_permissions=True)
    sm.submit()
    
    # Update CLN using db_set
    frappe.db.set_value("Convertible Loan Note", cln.name, {
        "status": "Converted",
        "conversion_date": frappe.utils.today(),
        "conversion_price": conversion_price,
        "shares_issued": num_shares,
        "total_converted_amount": total_amount,
        "share_transfer_ref": sm.name,
        "conversion_journal_entry_ref": je.name
    })
    
    # Update Shareholder
    shareholder = frappe.get_doc("Shareholder", cln.lender)
    shareholder.custom_has_convertible_loans = 0
    shareholder.custom_total_cln_amount = frappe.db.sql("""
        SELECT SUM(principal_amount)
        FROM `tabConvertible Loan Note`
        WHERE lender = %s AND status = 'Active' AND docstatus = 1
    """, cln.lender)[0][0] or 0
    shareholder.save(ignore_permissions=True)
    recalculate_shareholder_totals(cln.lender)

    frappe.db.commit()

    frappe.msgprint(_("Successfully converted CLN to {0} shares. Journal Entry: {1}, Share Movement: {2}").format(
        num_shares, je.name, sm.name
    ))
    
    return {
        "journal_entry": je.name,
        "share_movement": sm.name,
        "shares_issued": num_shares,
        "conversion_price": conversion_price,
        "total_amount": total_amount
    }


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_conversion_price(cln, next_round_price=None, fully_diluted_shares=None):
    """Calculate conversion price based on CLN terms"""
    conversion_price = None
    
    if next_round_price and cln.conversion_discount_rate:
        discounted_price = float(next_round_price) * (1 - (cln.conversion_discount_rate / 100))
        conversion_price = discounted_price
    
    if cln.valuation_cap and fully_diluted_shares:
        cap_price = cln.valuation_cap / float(fully_diluted_shares)
        
        if conversion_price:
            conversion_price = min(conversion_price, cap_price)
        else:
            conversion_price = cap_price
    
    if not conversion_price:
        frappe.throw(_("Please provide next_round_price and/or valuation_cap with fully_diluted_shares"))
    
    return conversion_price


def create_cln_conversion_journal_entry(cln, total_amount, share_capital_amount, share_premium_amount, 
                                        loan_currency, company_currency, exchange_rate):
    """Create journal entry for CLN conversion
    
    ACCOUNTING LOGIC:
    Dr: Loan Liability (clearing the debt)
    Dr: Interest Payable (if any) (clearing accrued interest)
        Cr: Share Capital (issuing shares at par)
        Cr: Share Premium (if any) (premium over par)
    """
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": frappe.utils.today(),
        "company": cln.company,
        "multi_currency": 1 if loan_currency != company_currency else 0,
        "user_remark": "Conversion of CLN {0} to {1} shares - settling liability with equity".format(
            cln.name, int(total_amount / (share_capital_amount / (total_amount - share_premium_amount) if (total_amount - share_premium_amount) > 0 else 1))
        ),
        "accounts": []
    })
    
    # Dr: Loan Liability (clearing principal)
    je.append("accounts", {
        "account": cln.loan_liability_account,
        "debit_in_account_currency": cln.principal_amount,
        "account_currency": loan_currency,
        "exchange_rate": exchange_rate,
        "party_type": "Shareholder",
        "party": cln.lender,
        # "reference_type": "Convertible Loan Note",
        # "reference_name": cln.name,
        "company": cln.company
    })
    
    # Dr: Interest Payable (if exists - clearing accrued interest)
    if cln.accrued_interest and cln.accrued_interest > 0:
        je.append("accounts", {
            "account": cln.interest_payable_account or cln.loan_liability_account,
            "debit_in_account_currency": cln.accrued_interest,
            "account_currency": loan_currency,
            "exchange_rate": exchange_rate,
            "party_type": "Shareholder",
            "party": cln.lender,
            "company": cln.company
        })
    
    # Cr: Share Capital (issuing shares at par value)
    je.append("accounts", {
        "account": cln.share_capital_account,
        "credit_in_account_currency": share_capital_amount,
        "account_currency": loan_currency,
        "exchange_rate": exchange_rate,
        "company": cln.company
    })
    
    # Cr: Share Premium (if any - premium over par value)
    if share_premium_amount > 0:
        je.append("accounts", {
            "account": cln.share_premium_account,
            "credit_in_account_currency": share_premium_amount,
            "account_currency": loan_currency,
            "exchange_rate": exchange_rate,
            "company": cln.company
        })
    
    je.insert(ignore_permissions=True)
    je.submit()

    return je


# ============================================
# SHARE REGISTER QUERY
# ============================================

@frappe.whitelist()
def get_share_register(company, as_on_date=None, share_class=None):
    """Get share register showing current shareholdings"""
    if not as_on_date:
        as_on_date = frappe.utils.today()
    
    conditions = ["sm.company = %(company)s", "sm.docstatus = 1", "sm.transaction_date <= %(as_on_date)s"]
    
    if share_class:
        conditions.append("sm.share_class = %(share_class)s")
    
    query = """
        SELECT
            sm.to_shareholder,
            sh.title as shareholder_name,
            sm.share_class,
            SUM(CASE WHEN sm.movement_type IN ('Equity Capital Injection', 'Share Purchase', 'Loan Equity Injection')
                THEN sm.number_of_shares ELSE 0 END) as shares_acquired,
            SUM(CASE WHEN sm.movement_type = 'Share Buyback'
                THEN -sm.number_of_shares ELSE 0 END) as shares_transferred,
            SUM(CASE WHEN sm.movement_type IN ('Equity Capital Injection', 'Share Purchase', 'Loan Equity Injection')
                THEN sm.number_of_shares
                WHEN sm.movement_type = 'Share Buyback'
                THEN -sm.number_of_shares
                ELSE 0 END) as current_holding,
            SUM(sm.total_amount_base_currency) as total_investment
        FROM `tabShare Movement` sm
        LEFT JOIN `tabShareholder` sh ON sm.to_shareholder = sh.name
        WHERE {conditions}
        GROUP BY sm.to_shareholder, sm.share_class
        HAVING current_holding > 0
        ORDER BY current_holding DESC
    """.format(conditions=" AND ".join(conditions))
    
    data = frappe.db.sql(query, {
        "company": company,
        "as_on_date": as_on_date,
        "share_class": share_class
    }, as_dict=1)
    
    # Calculate ownership percentages
    total_shares = sum([d.current_holding for d in data])
    
    for row in data:
        row.ownership_percentage = (row.current_holding / total_shares * 100) if total_shares > 0 else 0
    
    return data

