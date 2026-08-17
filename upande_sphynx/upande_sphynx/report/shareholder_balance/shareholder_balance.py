# Copyright (c) 2026, Jeniffer and contributors
# For license information, please see license.txt
#
# Replacement for ERPNext's standard "Share Balance" report. That report
# only reads Shareholder.share_balance, a child table ERPNext populates
# from Share Transfer alone — it never reflects shares issued via Share
# Agreement -> Share Movement or converted from a Convertible Loan Note,
# which are this app's primary equity-issuance paths. This report is
# computed directly from submitted Share Movements instead, and — unlike
# the standard report's unused "date" filter — actually honors "as on
# date".

import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.company:
		frappe.throw(_("Please select a Company"))

	filters.as_on_date = filters.as_on_date or today()

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Shareholder"), "fieldname": "shareholder", "fieldtype": "Link", "options": "Shareholder", "width": 180},
		{"label": _("Share Class"), "fieldname": "share_class", "fieldtype": "Link", "options": "Share Type", "width": 150},
		{"label": _("Shares Acquired"), "fieldname": "shares_acquired", "fieldtype": "Int", "width": 120},
		{"label": _("Shares Given Up"), "fieldname": "shares_given_up", "fieldtype": "Int", "width": 120},
		{"label": _("Current Holding"), "fieldname": "current_holding", "fieldtype": "Int", "width": 130},
		{"label": _("Total Investment"), "fieldname": "total_investment", "fieldtype": "Float", "width": 150},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	base_conditions = ["sm.company = %(company)s", "sm.docstatus = 1", "sm.transaction_date <= %(as_on_date)s"]
	if filters.share_class:
		base_conditions.append("sm.share_class = %(share_class)s")
	if filters.shareholder:
		base_conditions.append("holders.holder = %(shareholder)s")

	# signed_qty is the per-row delta from this holder's point of view: positive
	# when shares moved to them, negative when they gave shares up — regardless
	# of whether that direction came from to_shareholder/from_shareholder or
	# from a movement recorded with a negative number_of_shares. Deriving it
	# once here (rather than re-deriving acquired/given-up separately from
	# to_shareholder/from_shareholder) is what keeps a negative-quantity "out"
	# movement from being silently absorbed into "Shares Acquired" instead of
	# showing up under "Shares Given Up".
	query = """
		SELECT
			holder AS shareholder,
			share_class,
			SUM(CASE WHEN signed_qty > 0 THEN signed_qty ELSE 0 END) AS shares_acquired,
			SUM(CASE WHEN signed_qty < 0 THEN -signed_qty ELSE 0 END) AS shares_given_up,
			SUM(signed_qty) AS current_holding,
			SUM(CASE WHEN signed_qty > 0 AND movement_type != 'Share Buyback' THEN total_amount ELSE 0 END) AS total_investment,
			MAX(transaction_currency) AS currency
		FROM (
			SELECT
				sm.share_class AS share_class,
				sm.movement_type AS movement_type,
				sm.transaction_currency AS transaction_currency,
				sm.total_amount AS total_amount,
				holders.holder AS holder,
				CASE WHEN holders.holder = sm.to_shareholder THEN sm.number_of_shares ELSE -sm.number_of_shares END AS signed_qty
			FROM `tabShare Movement` sm
			JOIN (
				SELECT name, to_shareholder AS holder FROM `tabShare Movement`
				UNION
				SELECT name, from_shareholder AS holder FROM `tabShare Movement` WHERE from_shareholder IS NOT NULL AND from_shareholder != ''
			) holders ON holders.name = sm.name
			WHERE {conditions}
		) x
		GROUP BY holder, share_class
		HAVING current_holding != 0
	"""

	return frappe.db.sql(
		query.format(conditions=" AND ".join(base_conditions)) + " ORDER BY share_class, current_holding DESC",
		filters,
		as_dict=True,
	)
