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
from frappe.utils import flt, today


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
		{"label": _("Ownership %"), "fieldname": "ownership_percentage", "fieldtype": "Percent", "width": 110},
		{"label": _("Total Investment"), "fieldname": "total_investment", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	base_conditions = ["sm.company = %(company)s", "sm.docstatus = 1", "sm.transaction_date <= %(as_on_date)s"]
	if filters.share_class:
		base_conditions.append("sm.share_class = %(share_class)s")

	query = """
		SELECT
			holder AS shareholder,
			sm.share_class AS share_class,
			SUM(CASE WHEN sm.to_shareholder = holder THEN sm.number_of_shares ELSE 0 END) AS shares_acquired,
			SUM(CASE WHEN sm.from_shareholder = holder THEN sm.number_of_shares ELSE 0 END) AS shares_given_up,
			SUM(CASE WHEN sm.to_shareholder = holder THEN sm.number_of_shares ELSE -sm.number_of_shares END) AS current_holding,
			SUM(CASE WHEN sm.to_shareholder = holder AND sm.movement_type != 'Share Buyback'
				THEN sm.total_amount_base_currency ELSE 0 END) AS total_investment
		FROM `tabShare Movement` sm
		JOIN (
			SELECT name, to_shareholder AS holder FROM `tabShare Movement`
			UNION
			SELECT name, from_shareholder AS holder FROM `tabShare Movement` WHERE from_shareholder IS NOT NULL AND from_shareholder != ''
		) holders ON holders.name = sm.name
		WHERE {conditions}
		GROUP BY holder, sm.share_class
		HAVING current_holding != 0
	"""

	# Class-wide totals (never shareholder-filtered) so ownership % stays correct
	# even when the report is narrowed to a single shareholder.
	class_totals = frappe.db.sql(
		query.format(conditions=" AND ".join(base_conditions)) + " ORDER BY sm.share_class",
		filters,
		as_dict=True,
	)
	totals_by_class = {}
	for row in class_totals:
		totals_by_class[row.share_class] = totals_by_class.get(row.share_class, 0) + row.current_holding

	display_conditions = list(base_conditions)
	if filters.shareholder:
		display_conditions.append("holders.holder = %(shareholder)s")

	rows = frappe.db.sql(
		query.format(conditions=" AND ".join(display_conditions)) + " ORDER BY sm.share_class, current_holding DESC",
		filters,
		as_dict=True,
	)

	for row in rows:
		class_total = totals_by_class.get(row.share_class) or 0
		row.ownership_percentage = flt(row.current_holding / class_total * 100, 2) if class_total else 0

	return rows
