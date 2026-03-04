# Copyright (c) 2026, Jeniffer and contributors
# For license information, please see license.txt

# Copyright (c) 2024
# Custom Accounts Payable Aging Report
# License: GNU General Public License v3

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.report_date:
        filters.report_date = nowdate()

    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 180,
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 160,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
        },
        {
            "label": _("Invoiced Amount"),
            "fieldname": "invoiced",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": _("Paid Amount"),
            "fieldname": "paid",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130,
        },
        {
            "label": _("Outstanding"),
            "fieldname": "outstanding",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Age (Days)"),
            "fieldname": "age",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": _("Aging Bucket"),
            "fieldname": "aging_bucket",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("0-30"),
            "fieldname": "range1",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": _("31-60"),
            "fieldname": "range2",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": _("61-90"),
            "fieldname": "range3",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": _("91-120"),
            "fieldname": "range4",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": _("121+"),
            "fieldname": "range5",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
    ]


def get_data(filters):
    report_date = getdate(filters.report_date)
    company = filters.get("company")

    # ── Build WHERE conditions and values dict together ──────────────────────
    # IMPORTANT: every %(key)s used in conditions MUST exist in values dict.
    conditions = ["gle.company = %(company)s"]
    values = {
        "company": company,
        "report_date": report_date,
    }

    # Optional: specific payable account
    party_account = filters.get("party_account")
    if party_account:
        conditions.append("gle.account = %(party_account)s")
        values["party_account"] = party_account  # added to values at same time

    # Optional: one or more suppliers (MultiSelectList arrives as list, possibly with empty strings)
    party = filters.get("party")
    if isinstance(party, list):
        party = [p for p in party if p]  # drop empty strings from blank multiselect
    if party:
        if isinstance(party, list) and len(party) == 1:
            conditions.append("gle.party = %(party_single)s")
            values["party_single"] = party[0]
        elif isinstance(party, list):
            conditions.append("gle.party IN %(party)s")
            values["party"] = tuple(party)
        else:
            conditions.append("gle.party = %(party)s")
            values["party"] = party

    where_clause = " AND ".join(conditions)

    # ── Main GL query ──────────────────────────────────────────────────────────
    entries = frappe.db.sql(
        """
        SELECT
            gle.party                       AS supplier,
            gle.voucher_type,
            gle.voucher_no,
            gle.posting_date,
            gle.account_currency            AS currency,
            SUM(CASE
                WHEN gle.debit_in_account_currency  > 0
                THEN gle.debit_in_account_currency  ELSE 0 END) AS debit,
            SUM(CASE
                WHEN gle.credit_in_account_currency > 0
                THEN gle.credit_in_account_currency ELSE 0 END) AS credit
        FROM
            `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE
            gle.party_type   = 'Supplier'
            AND gle.posting_date <= %(report_date)s
            AND gle.is_cancelled  = 0
            AND acc.account_type  = 'Payable'
            AND {where_clause}
        GROUP BY
            gle.voucher_no, gle.party
        HAVING
            (SUM(gle.credit_in_account_currency)
             - SUM(gle.debit_in_account_currency)) > 0.005
        ORDER BY
            gle.party, gle.posting_date
        """.format(where_clause=where_clause),
        values,
        as_dict=True,
    )

    if not entries:
        return []

    # ── Fetch due dates from Purchase Invoice via get_all (avoids tuple-of-one issues) ──
    voucher_nos = list({e.voucher_no for e in entries})
    due_dates = {}

    if voucher_nos:
        pi_records = frappe.db.get_all(
            "Purchase Invoice",
            filters={"name": ["in", voucher_nos]},
            fields=["name", "due_date"],
        )
        for pi in pi_records:
            due_dates[pi.name] = pi.due_date

    # ── Build output rows ──────────────────────────────────────────────────────
    data = []
    for entry in entries:
        outstanding = flt(entry.credit) - flt(entry.debit)
        if outstanding <= 0.005:
            continue

        due_date = getdate(due_dates.get(entry.voucher_no) or entry.posting_date)
        age_days  = (report_date - due_date).days
        status    = "Overdue" if age_days > 0 else "Current"

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
            "supplier":     entry.supplier,
            "voucher_type": entry.voucher_type,
            "voucher_no":   entry.voucher_no,
            "posting_date": entry.posting_date,
            "due_date":     due_date,
            "currency":     entry.currency,
            "invoiced":     flt(entry.credit),
            "paid":         flt(entry.debit),
            "outstanding":  outstanding,
            "status":       status,
            "age":          max(age_days, 0),
            "aging_bucket": bucket,
            "range1":       outstanding if age_days <= 30               else 0,
            "range2":       outstanding if 30  < age_days <= 60         else 0,
            "range3":       outstanding if 60  < age_days <= 90         else 0,
            "range4":       outstanding if 90  < age_days <= 120        else 0,
            "range5":       outstanding if age_days > 120               else 0,
        })

    return data