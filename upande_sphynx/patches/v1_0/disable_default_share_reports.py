"""Hide ERPNext's standard Share Ledger / Share Balance reports.

Both only read data ERPNext itself tracks via Share Transfer (and, for
Share Balance, the Shareholder.share_balance child table Share Transfer
populates). Neither reflects shares issued via Share Agreement -> Share
Movement or converted from a Convertible Loan Note, which are this app's
primary equity paths — so both would silently show an incomplete picture
if left enabled alongside this app's own reports (Share Transactions
Report, Shareholder Balance).

This only disables them (reversible from Report list, uncheck "Disabled")
rather than deleting them, since they're owned by erpnext, not this app.
"""

import frappe


def execute():
	for report_name in ("Share Ledger", "Share Balance"):
		if frappe.db.exists("Report", report_name):
			frappe.db.set_value("Report", report_name, "disabled", 1)
