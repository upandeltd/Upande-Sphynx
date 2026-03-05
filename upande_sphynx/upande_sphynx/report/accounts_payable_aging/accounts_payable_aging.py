# Copyright (c) 2026, Jeniffer and contributors
# For license information, please see license.txt

# Copyright (c) 2024 Upande Sphynx
# Accounts Payable Aging — Script Report
# Queries Purchase Invoice directly (not GL Entry) so only real supplier
# invoices appear, with accurate outstanding amounts as computed by ERPNext.

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, date_diff


def execute(filters=None):
    filters = frappe._dict(filters or {})

    if not filters.from_date:
        filters.from_date = frappe.defaults.get_user_default("year_start_date") or "2000-01-01"
    if not filters.to_date:
        filters.to_date = nowdate()

    validate_filters(filters)
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


def validate_filters(filters):
    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date"))


def get_columns():
    return [
        {
            "label":     _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options":   "Supplier",
            "width":     190,
        },
        {
            "label":     _("Invoice No"),
            "fieldname": "invoice_no",
            "fieldtype": "Link",
            "options":   "Purchase Invoice",
            "width":     160,
        },
        {
            "label":     _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width":     110,
        },
        {
            "label":     _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width":     110,
        },
        {
            "label":     _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options":   "Currency",
            "width":     75,
        },
        {
            "label":     _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     140,
        },
        {
            "label":     _("Paid Amount"),
            "fieldname": "paid_amount",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     130,
        },
        {
            "label":     _("Outstanding"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     140,
        },
        {
            "label":     _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width":     95,
        },
        {
            "label":     _("Age (Days)"),
            "fieldname": "age_days",
            "fieldtype": "Int",
            "width":     90,
        },
        {
            "label":     _("Aging Bucket"),
            "fieldname": "aging_bucket",
            "fieldtype": "Data",
            "width":     105,
        },
        {
            "label":     _("0-30"),
            "fieldname": "range1",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     120,
        },
        {
            "label":     _("31-60"),
            "fieldname": "range2",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     120,
        },
        {
            "label":     _("61-90"),
            "fieldname": "range3",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     120,
        },
        {
            "label":     _("91-120"),
            "fieldname": "range4",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     120,
        },
        {
            "label":     _("121+"),
            "fieldname": "range5",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     120,
        },
    ]


def get_data(filters):
    from_date    = getdate(filters.from_date)
    to_date      = getdate(filters.to_date)
    age_ref_date = to_date   # ageing is calculated as of the To Date

    # ── Build conditions safely ───────────────────────────────────────────────
    conditions = [
        "pi.docstatus = 1",                          # submitted invoices only
        "pi.outstanding_amount > 0.005",             # has a real balance
        "pi.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]
    values = {
        "from_date": from_date,
        "to_date":   to_date,
    }

    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
        values["company"] = filters.company

    if filters.get("party_account"):
        conditions.append("pi.credit_to = %(party_account)s")
        values["party_account"] = filters.party_account

    if filters.get("supplier_group"):
        conditions.append("sup.supplier_group = %(supplier_group)s")
        values["supplier_group"] = filters.supplier_group

    # party filter — MultiSelectList arrives as list, possibly with empty strings
    party = filters.get("party")
    if isinstance(party, list):
        party = [p for p in party if p]
    if party:
        if isinstance(party, list) and len(party) == 1:
            conditions.append("pi.supplier = %(supplier_single)s")
            values["supplier_single"] = party[0]
        elif isinstance(party, list):
            conditions.append("pi.supplier IN %(party)s")
            values["party"] = tuple(party)
        else:
            conditions.append("pi.supplier = %(party)s")
            values["party"] = party

    where = " AND ".join(conditions)

    invoices = frappe.db.sql(
        """
        SELECT
            pi.name                                        AS invoice_no,
            pi.supplier,
            pi.supplier_name,
            pi.posting_date,
            pi.due_date,
            pi.currency,
            pi.grand_total,
            pi.outstanding_amount,
            (pi.grand_total - pi.outstanding_amount)       AS paid_amount
        FROM
            `tabPurchase Invoice` pi
            LEFT JOIN `tabSupplier` sup ON sup.name = pi.supplier
        WHERE
            {where}
        ORDER BY
            pi.supplier, pi.posting_date
        """.format(where=where),
        values,
        as_dict=True,
    )

    if not invoices:
        return []

    data = []
    for inv in invoices:
        due_date = getdate(inv.due_date or inv.posting_date)
        age_days = date_diff(age_ref_date, due_date)   # positive = days past due
        out_amt  = flt(inv.outstanding_amount)

        status = "Overdue" if age_days > 0 else "Current"

        if age_days <= 30:
            bucket = "0-30"
        elif age_days <= 60:
            bucket = "31-60"
        elif age_days <= 90:
            bucket = "61-90"
        elif age_days <= 120:
            bucket = "91-120"
        else:
            bucket = "121+"

        data.append({
            "supplier":           inv.supplier,
            "invoice_no":         inv.invoice_no,
            "posting_date":       inv.posting_date,
            "due_date":           due_date,
            "currency":           inv.currency,
            "grand_total":        flt(inv.grand_total),
            "paid_amount":        flt(inv.paid_amount),
            "outstanding_amount": out_amt,
            "status":             status,
            "age_days":           max(age_days, 0),
            "aging_bucket":       bucket,
            "range1":             out_amt if age_days <= 30          else 0,
            "range2":             out_amt if 30  < age_days <= 60    else 0,
            "range3":             out_amt if 60  < age_days <= 90    else 0,
            "range4":             out_amt if 90  < age_days <= 120   else 0,
            "range5":             out_amt if age_days > 120          else 0,
        })

    return data
