"""Add Connections (Document Links) to the standard Shareholder doctype.

Document Links for a doctype this app doesn't own can't be shipped via the
`custom/<doctype>.json` customization format — Frappe's customization sync
only processes `custom_fields`, `property_setters`, and `custom_perms` from
that file; a `links` key there is silently ignored. This patch adds them
directly to the Shareholder DocType record instead, idempotently.

Note on `custom`: Customize Form marks user-added links with `custom=1` so
they survive a core reload of the doctype. That flag also makes Frappe's
Meta builder re-fetch and re-append every `custom=1` row on top of the
normal load — which double-counted these into duplicate Connections tab
entries when tested (Shareholder has no native links of its own, so there
was nothing for the "normal load" and the "custom re-fetch" to be
distinguishing between; they loaded the exact same rows twice). Using
`custom=0` avoids that, matching how Share Agreement/Share Movement/CLN's
own native links already behave with no duplication. The small trade-off:
if ERPNext ever ships a Shareholder doctype update that specifically
reloads its link table from scratch, these could be wiped and would need
re-adding (re-run this patch's `execute()` manually if that ever happens —
it's idempotent).
"""

import frappe

LINKS = [
	{"group": "Agreements", "link_doctype": "Share Agreement", "link_fieldname": "shareholder"},
	{"group": "Shares Received", "link_doctype": "Share Movement", "link_fieldname": "to_shareholder"},
	{"group": "Shares Given Up", "link_doctype": "Share Movement", "link_fieldname": "from_shareholder"},
	{"group": "Loans", "link_doctype": "Convertible Loan Note", "link_fieldname": "lender"},
	{"group": "Transfers Received", "link_doctype": "Share Transfer", "link_fieldname": "to_shareholder"},
	{"group": "Transfers Given", "link_doctype": "Share Transfer", "link_fieldname": "from_shareholder"},
]


def execute():
	existing = set(
		frappe.db.sql(
			"SELECT link_doctype, link_fieldname FROM `tabDocType Link` WHERE parent = 'Shareholder'"
		)
	)

	for link in LINKS:
		key = (link["link_doctype"], link["link_fieldname"])
		if key in existing:
			continue
		frappe.get_doc({
			"doctype": "DocType Link",
			"parent": "Shareholder",
			"parenttype": "DocType",
			"parentfield": "links",
			"custom": 0,
			**link,
		}).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Shareholder")
	frappe.db.commit()
