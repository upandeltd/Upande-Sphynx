# Copyright (c) 2025
# Shareholder Transactions Report (Refactored & Optimized)

import frappe
from frappe import _
from frappe.utils import flt


# -----------------------------
# REPORT ENTRY POINT
# -----------------------------
def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


# -----------------------------
# COLUMNS
# -----------------------------
def get_columns():
    return [
        {"fieldname": "transaction_date", "label": _("Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "shareholder", "label": _("Shareholder"), "fieldtype": "Link", "options": "Shareholder", "width": 180},
        {"fieldname": "transaction_type", "label": _("Transaction Type"), "fieldtype": "Data", "width": 150},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
        {"fieldname": "movement_type", "label": _("Movement Type"), "fieldtype": "Data", "width": 200},
        {"fieldname": "share_class", "label": _("Share Class"), "fieldtype": "Link", "options": "Share Type", "width": 120},
        {"fieldname": "shares_in", "label": _("Shares In"), "fieldtype": "Int", "width": 100},
        {"fieldname": "shares_out", "label": _("Shares Out"), "fieldtype": "Int", "width": 100},
        {"fieldname": "price_per_share", "label": _("Price/Share"), "fieldtype": "Currency", "options": "currency", "width": 120},
        {"fieldname": "exchange_rate", "label": _("Exchange Rate"), "fieldtype": "Float", "width": 120},
        {"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "options": "currency", "width": 130},
        {"fieldname": "currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "width": 80},
        # {"fieldname": "cumulative_shares", "label": _("Cumulative Shares"), "fieldtype": "Int", "width": 130},
        # {"fieldname": "ownership_percentage", "label": _("Ownership %"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "source_document", "label": _("Source Document"), "fieldtype": "Data", "width": 180},
        {"fieldname": "reference", "label": _("Reference"), "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 150},
        {"fieldname": "reference_doctype", "label": _("Reference DocType"), "fieldtype": "Data", "hidden": 1},
    ]


# -----------------------------
# CORE DATA FUNCTION
# -----------------------------
def get_data(filters):

    cond = build_conditions(filters)

    sql = f"""
        -- SHARE MOVEMENTS
        SELECT 
            sm.transaction_date,
            sm.to_shareholder AS shareholder,
            sh.title,
            'Share Movement' AS transaction_type,
            sm.movement_type,
            sm.share_class,
            CASE 
                WHEN sm.movement_type IN (
                    'Equity Capital Injection', 'Share Subscription', 'Share Purchase',
                    'Loan Equity Injection', 'Bonus Issue', 'Rights Issue'
                ) THEN sm.number_of_shares ELSE 0 END AS shares_in,
            CASE 
                WHEN sm.movement_type IN ('Share Transfer', 'Share Buyback')
                AND sm.from_shareholder = sm.to_shareholder
                THEN sm.number_of_shares ELSE 0 END AS shares_out,
            sm.price_per_share,
            sm.exchange_rate,
            sm.total_amount AS amount,
            sm.transaction_currency AS currency,
            sm.source_document_type,
            sm.source_document_name,
            sm.status,
            sm.name AS reference,
            'Share Movement' AS reference_doctype,
            sm.company
        FROM `tabShare Movement` sm
        LEFT JOIN `tabShareholder` sh ON sm.to_shareholder = sh.name
        WHERE sm.docstatus = 1 {cond['sm']}

        UNION ALL

        -- CLN LOANS
        SELECT
            cln.issue_date,
            cln.lender AS shareholder,
            sh.title,
            'CLN Loan' AS transaction_type,
            'Loan Disbursement' AS movement_type,
            NULL AS share_class,
            0 AS shares_in,
            0 AS shares_out,
            NULL AS price_per_share,
            cln.exchange_rate,
            cln.principal_amount AS amount,
            cln.loan_currency AS currency,
            'Convertible Loan Note' AS source_document_type,
            cln.name AS source_document_name,
            cln.status,
            cln.name AS reference,
            'Convertible Loan Note' AS reference_doctype,
            cln.company
        FROM `tabConvertible Loan Note` cln
        LEFT JOIN `tabShareholder` sh ON cln.lender = sh.name
        WHERE cln.docstatus = 1
        AND cln.status != 'Draft' {cond['cln']}

        ORDER BY transaction_date DESC, shareholder
    """

    movements = frappe.db.sql(sql, filters, as_dict=1)

    # Process cumulative share holdings
    return process_cumulative(movements, filters)


# -----------------------------
# BUILD CONDITIONS SAFELY
# -----------------------------
def build_conditions(filters):

    sm = []
    cln = []

    if filters.get("company"):
        sm.append("AND sm.company = %(company)s")
        cln.append("AND cln.company = %(company)s")

    if filters.get("shareholder"):
        sm.append("AND sm.to_shareholder = %(shareholder)s")
        cln.append("AND cln.lender = %(shareholder)s")

    if filters.get("share_class"):
        sm.append("AND sm.share_class = %(share_class)s")

    if filters.get("from_date"):
        sm.append("AND sm.transaction_date >= %(from_date)s")
        cln.append("AND cln.issue_date >= %(from_date)s")

    if filters.get("to_date"):
        sm.append("AND sm.transaction_date <= %(to_date)s")
        cln.append("AND cln.issue_date <= %(to_date)s")

    if filters.get("movement_type"):
        sm.append("AND sm.movement_type = %(movement_type)s")

    return {
        "sm": " " + " ".join(sm) if sm else "",
        "cln": " " + " ".join(cln) if cln else "",
    }


# -----------------------------
# PROCESS CUMULATIVE HOLDINGS
# -----------------------------
def process_cumulative(movements, filters):

    holdings = {}  # shareholder+class → shares
    totals = get_total_shares(filters)

    processed = []

    for row in movements:

        key = f"{row.shareholder}_{row.share_class}"

        if key not in holdings:
            holdings[key] = 0

        # Net movement
        net = row.shares_in - row.shares_out
        holdings[key] += net
        row.cumulative_shares = holdings[key]

        # Ownership %
        if row.share_class and totals.get(row.share_class):
            row.ownership_percentage = (holdings[key] / totals[row.share_class]) * 100
        else:
            row.ownership_percentage = 0

        # Source Document
        if row.source_document_type and row.source_document_name:
            row.source_document = f"{row.source_document_type}: {row.source_document_name}"
        else:
            row.source_document = ""

        processed.append(row)

    return processed


# -----------------------------
# TOTAL SHARES BY CLASS
# -----------------------------
def get_total_shares(filters):

    where = "WHERE sm.docstatus = 1"
    if filters.get("company"):
        where += " AND sm.company = %(company)s"

    sql = f"""
        SELECT 
            share_class,
            SUM(CASE 
                WHEN movement_type IN (
                    'Equity Capital Injection', 'Share Subscription', 'Share Purchase',
                    'Loan Equity Injection', 'Bonus Issue', 'Rights Issue'
                ) THEN number_of_shares
                WHEN movement_type IN ('Share Transfer', 'Share Buyback')
                THEN -number_of_shares
                ELSE 0 END
            ) AS total
        FROM `tabShare Movement` sm
        {where}
        GROUP BY share_class
    """

    rows = frappe.db.sql(sql, filters, as_dict=True)
    return {r.share_class: flt(r.total) for r in rows}
