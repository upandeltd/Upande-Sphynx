// Copyright (c) 2026, Jeniffer and contributors
// For license information, please see license.txt

frappe.query_reports["Shareholder Balance"] = {
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
			"fieldname": "as_on_date",
			"label": __("As On Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
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
		}
	]
};
