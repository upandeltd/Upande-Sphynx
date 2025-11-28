// Copyright (c) 2025, Jeniffer and contributors
// For license information, please see license.txt

frappe.query_reports["Share Transactions Report"] = {

    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "shareholder",
            "label": __("Shareholder"),
            "fieldtype": "Link",
            "options": "Shareholder"
        },
        {
            "fieldname": "share_class",
            "label": __("Share Class"),
            "fieldtype": "Link",
            "options": "Share Type"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "movement_type",
            "label": __("Movement Type"),
            "fieldtype": "Select",
            "options": "\nEquity Capital Injection\nShare Purchase\nLoan Equity Injection\nShare Transfer\nShare Buyback\nBonus Issue\nRights Issue\nShare Split\nShare Consolidation"
        }
    ]
};
