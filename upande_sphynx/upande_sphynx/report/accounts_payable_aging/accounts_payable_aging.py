# Copyright (c) 2026, Jeniffer and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, date_diff


def execute(filters=None):
    filters = frappe._dict(filters or {})

    if not filters.from_date:
        filters.from_date = frappe.defaults.get_user_default("year_start_date") or "2000-01-01"
    if not filters.to_date:
        filters.to_date = nowdate()

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date"))

    columns = get_columns()
    data    = get_data(filters)
    return columns, data


# ── Columns ───────────────────────────────────────────────────────────────────
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
            "label":     _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width":     120,
        },
        {
            "label":     _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width":     120,
        },
        {
            "label":     _("Invoice No"),
            "fieldname": "invoice_no",
            "fieldtype": "Link",
            "options":   "Purchase Invoice",
            "width":     160,
        },
		
		{
            "label":     _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width":     95,
        },

        {
            "label":     _("Outstanding"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "options":   "currency",
            "width":     170,
        },
        
        {
            "label":     _("Age (Days)"),
            "fieldname": "age_days",
            "fieldtype": "Int",
            "width":     90,
        },
        # {
        #     "label":     _("Aging Bucket"),
        #     "fieldname": "aging_bucket",
        #     "fieldtype": "Data",
        #     "width":     105,
        # },
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


# ── Data ──────────────────────────────────────────────────────────────────────
def get_data(filters):
    from_date    = getdate(filters.from_date)
    to_date      = getdate(filters.to_date)
    age_ref_date = to_date

    # ── Step 1: fetch all submitted Purchase Invoices in the date range ───────
    inv_conditions = [
        "pi.docstatus = 1",
        "pi.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]
    inv_values = {
        "from_date": from_date,
        "to_date":   to_date,
    }

    if filters.get("company"):
        inv_conditions.append("pi.company = %(company)s")
        inv_values["company"] = filters.company

    if filters.get("party_account"):
        inv_conditions.append("pi.credit_to = %(party_account)s")
        inv_values["party_account"] = filters.party_account

    if filters.get("supplier_group"):
        inv_conditions.append("sup.supplier_group = %(supplier_group)s")
        inv_values["supplier_group"] = filters.supplier_group

    party = filters.get("party")
    if isinstance(party, list):
        party = [p for p in party if p]
    if party:
        if isinstance(party, list) and len(party) == 1:
            inv_conditions.append("pi.supplier = %(supplier_single)s")
            inv_values["supplier_single"] = party[0]
        elif isinstance(party, list):
            inv_conditions.append("pi.supplier IN %(party)s")
            inv_values["party"] = tuple(party)
        else:
            inv_conditions.append("pi.supplier = %(party)s")
            inv_values["party"] = party

    invoices = frappe.db.sql(
        """
        SELECT
            pi.name          AS invoice_no,
            pi.supplier,
            pi.posting_date,
            pi.due_date,
            pi.currency,
            pi.grand_total
        FROM
            `tabPurchase Invoice` pi
            LEFT JOIN `tabSupplier` sup ON sup.name = pi.supplier
        WHERE
            {where}
        ORDER BY
            pi.supplier, pi.posting_date
        """.format(where=" AND ".join(inv_conditions)),
        inv_values,
        as_dict=True,
    )

    if not invoices:
        return []

    voucher_nos = [inv.invoice_no for inv in invoices]

    # ── Step 2: reconstruct outstanding as of to_date from GL Entry ───────────
    # For each voucher, sum credits (= invoice postings) and debits
    # (= payments/credit notes) that occurred on or before to_date.
    # outstanding_as_of_to_date = credit_total - debit_total
    gl_rows = frappe.db.sql(
        """
        SELECT
            gle.voucher_no,
            SUM(CASE WHEN gle.credit_in_account_currency > 0
                THEN gle.credit_in_account_currency ELSE 0 END) AS total_credit,
            SUM(CASE WHEN gle.debit_in_account_currency  > 0
                THEN gle.debit_in_account_currency  ELSE 0 END) AS total_debit
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE
            gle.voucher_no   IN %(voucher_nos)s
            AND gle.party_type = 'Supplier'
            AND gle.is_cancelled = 0
            AND acc.account_type = 'Payable'
            AND gle.posting_date <= %(to_date)s
        GROUP BY gle.voucher_no
        """,
        {
            "voucher_nos": tuple(voucher_nos),
            "to_date":     to_date,
        },
        as_dict=True,
    )

    # Build a lookup: voucher_no -> outstanding as of to_date
    gl_map = {}
    for row in gl_rows:
        credit = flt(row.total_credit)
        debit  = flt(row.total_debit)
        gl_map[row.voucher_no] = {
            "outstanding": credit - debit,
            "paid":        debit,
        }

    # ── Step 3: build report rows ─────────────────────────────────────────────
    data = []
    for inv in invoices:
        gl = gl_map.get(inv.invoice_no, {})
        out_amt  = flt(gl.get("outstanding", inv.grand_total))
        paid_amt = flt(gl.get("paid", 0))

        # Skip invoices that were fully settled on or before to_date
        if out_amt <= 0.005:
            continue

        due_date = getdate(inv.due_date or inv.posting_date)
        age_days = date_diff(age_ref_date, due_date)
        status   = "Overdue" if age_days > 0 else "Current"

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
            "paid_amount":        paid_amt,
            "outstanding_amount": out_amt,
            "status":             status,
            "age_days":           max(age_days, 0),
            "aging_bucket":       bucket,
            "range1":             out_amt if age_days <= 30        else 0,
            "range2":             out_amt if 30  < age_days <= 60  else 0,
            "range3":             out_amt if 60  < age_days <= 90  else 0,
            "range4":             out_amt if 90  < age_days <= 120 else 0,
            "range5":             out_amt if age_days > 120        else 0,
        })

    return data
