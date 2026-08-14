"""Yearly Share Capital FX Revaluation.

Replaces the "Share Capital Currency Revaluation" Scheduler Event Server
Script, which defined a function `execute()` and never called it — every
year it fired, defined the function, and exited without running a single
line inside it. It also called `frappe.utils.get_exchange_rate`, which
doesn't exist (the correct function lives in `erpnext.setup.utils`), and
only looked at Share Transfer records, ignoring Share Movement and
Convertible Loan Note.

IMPORTANT — accounting treatment is not yet verified with an accountant.
The debit/credit direction implemented here (credit Share Capital when its
base-currency value rises, debit when it falls, offset against the
company's Unrealized Exchange Gain/Loss account) is a reasonable default
matching how ERPNext's own Exchange Rate Revaluation tool treats monetary
balances, but has not been confirmed for this company's specific policy.
For that reason the Journal Entry this creates is left as a **draft** for
review — it is deliberately not auto-submitted.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from erpnext.setup.utils import get_exchange_rate

REVALUATION_TAG = "Share Capital FX Revaluation"

# (doctype, currency fieldname, transaction-currency amount fieldname, historical exchange-rate fieldname)
REVALUATION_SOURCES = [
	("Share Transfer", "transaction_currency", "total_amount_in_transaction_currency", "exchange_rate"),
	("Share Movement", "transaction_currency", "total_amount", "exchange_rate"),
	("Convertible Loan Note", "loan_currency", "principal_amount", "exchange_rate"),
]


def revalue_share_capital_fx(dry_run=False):
	"""Yearly scheduled entry point. See module docstring for the caveat on
	the accounting treatment used here."""
	report = []

	for company in frappe.get_all(
		"Company",
		filters={"custom_share_capital_account": ["is", "set"]},
		fields=["name", "default_currency", "custom_share_capital_account", "unrealized_exchange_gain_loss_account"],
	):
		if not company.unrealized_exchange_gain_loss_account:
			frappe.log_error(
				f"Skipping {company.name}: no Unrealized Exchange Gain/Loss Account set on Company",
				REVALUATION_TAG,
			)
			continue

		report.extend(_revalue_company(company, dry_run=dry_run))

	return report


def _revalue_company(company, dry_run):
	base_currency = company.default_currency
	exposures = _aggregate_exposures(company.name, base_currency)
	results = []

	for currency, values in exposures.items():
		current_rate = get_exchange_rate(currency, base_currency)
		if not current_rate:
			frappe.log_error(f"No exchange rate found for {currency} -> {base_currency}", REVALUATION_TAG)
			continue

		new_in_base = flt(values["current_amount"]) * flt(current_rate)
		difference = flt(new_in_base - values["original_in_base"], 2)

		result = {
			"company": company.name,
			"currency": currency,
			"original_in_base": flt(values["original_in_base"], 2),
			"new_in_base": new_in_base,
			"difference": difference,
			"journal_entry": None,
		}

		if abs(difference) < 0.01:
			results.append(result)
			continue

		if not dry_run:
			je = _build_revaluation_entry(company, currency, difference)
			result["journal_entry"] = je.name

		results.append(result)

	return results


def _aggregate_exposures(company_name, base_currency):
	"""Sum transaction-currency amounts and their original base-currency
	value (using each record's own historical exchange rate) across Share
	Transfer, Share Movement, and Convertible Loan Note, grouped by
	currency. Base-currency records are excluded (nothing to revalue)."""
	exposures = {}

	for doctype, currency_field, amount_field, rate_field in REVALUATION_SOURCES:
		rows = frappe.get_all(
			doctype,
			filters={"company": company_name, "docstatus": 1},
			fields=[currency_field, amount_field, rate_field],
		)
		for row in rows:
			currency = row.get(currency_field)
			if not currency or currency == base_currency:
				continue

			amount = flt(row.get(amount_field))
			rate = flt(row.get(rate_field)) or 1.0

			bucket = exposures.setdefault(currency, {"current_amount": 0.0, "original_in_base": 0.0})
			bucket["current_amount"] += amount
			bucket["original_in_base"] += amount * rate

	return exposures


def _build_revaluation_entry(company, currency, difference):
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Exchange Rate Revaluation"
	je.company = company.name
	je.posting_date = getdate()
	je.user_remark = _(
		"Share Capital FX Revaluation for {0} — draft, review and confirm the debit/credit "
		"direction with your accountant before submitting."
	).format(currency)

	# A base-currency increase credits Share Capital (equity grows) and debits
	# the gain/loss account; a decrease is the reverse. See module docstring.
	share_capital_debit = abs(difference) if difference < 0 else 0
	share_capital_credit = difference if difference > 0 else 0
	gain_loss_debit = difference if difference > 0 else 0
	gain_loss_credit = abs(difference) if difference < 0 else 0

	je.append("accounts", {
		"account": company.custom_share_capital_account,
		"debit_in_account_currency": share_capital_debit,
		"credit_in_account_currency": share_capital_credit,
	})
	je.append("accounts", {
		"account": company.unrealized_exchange_gain_loss_account,
		"debit_in_account_currency": gain_loss_debit,
		"credit_in_account_currency": gain_loss_credit,
	})

	je.flags.ignore_permissions = True
	je.insert()
	frappe.db.commit()
	return je


@frappe.whitelist()
def run_share_capital_fx_revaluation(dry_run=1):
	"""Manual trigger for testing. Defaults to a dry run (no Journal Entry
	created) so the computed numbers can be reviewed safely before relying
	on the yearly scheduled job."""
	frappe.only_for(["System Manager", "Accounts Manager"])
	return revalue_share_capital_fx(dry_run=bool(int(dry_run)))
