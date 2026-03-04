// Copyright (c) 2026, Jeniffer and contributors
// For license information, please see license.txt


frappe.query_reports["Accounts Payable Aging"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "report_date",
			label: __("As Of Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "party_account",
			label: __("Payable Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
						account_type: "Payable",
						is_group: 0,
					},
				};
			},
		},
		{
			fieldname: "party",
			label: __("Supplier(s)"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Supplier", txt);
			},
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group",
		},
	],

	collapsible_filters: false,
	separate_check_filters: false,

	// ── Column formatter ──────────────────────────────────────────────────────
	formatter: function (value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);

		// Currency columns — render with symbol
		const currency_fields = [
			"invoiced", "paid", "outstanding",
			"range1", "range2", "range3", "range4", "range5",
		];

		if (currency_fields.includes(column.fieldname) && data.currency) {
			const symbol = frappe.get_currency_symbol(data.currency) || data.currency;
			const formatted_number = format_currency(flt(value), data.currency);
			value = `<span class="text-right d-block">${formatted_number}</span>`;
			return value;
		}

		// Status badge
		if (column.fieldname === "status") {
			if (value === "Overdue") {
				return `<span class="ap-badge ap-badge--overdue">${value}</span>`;
			} else if (value === "Current") {
				return `<span class="ap-badge ap-badge--current">${value}</span>`;
			}
		}

		// Aging bucket pill
		if (column.fieldname === "aging_bucket") {
			const bucket_class = {
				"0-30":   "bucket-0",
				"31-60":  "bucket-1",
				"61-90":  "bucket-2",
				"91-120": "bucket-3",
				"121+":   "bucket-4",
			}[value] || "bucket-0";
			return `<span class="ap-bucket ${bucket_class}">${value}</span>`;
		}

		// Bold totals rows
		if (data && data.bold) {
			value = default_formatter(value, row, column, data);
			return `<strong>${value}</strong>`;
		}

		return default_formatter(value, row, column, data);
	},

	// ── After render: inject styles + charts ─────────────────────────────────
	after_datatable_render: function (datatable_obj) {
		inject_ap_styles();
	},

	get_chart_data: function (columns, result) {
		if (!result || !result.length) return;

		// Aggregate outstanding by aging bucket
		const buckets = ["0-30", "31-60", "61-90", "91-120", "121+"];
		const bucket_fields = ["range1", "range2", "range3", "range4", "range5"];
		const totals = [0, 0, 0, 0, 0];
		let currency = "";

		result.forEach((row) => {
			if (!row.supplier) return; // skip summary rows
			if (!currency && row.currency) currency = row.currency;
			bucket_fields.forEach((f, i) => {
				totals[i] += flt(row[f]);
			});
		});

		const symbol = (currency && frappe.get_currency_symbol(currency)) || "";

		return {
			data: {
				labels: buckets,
				datasets: [
					{
						name: __("Outstanding"),
						values: totals,
					},
				],
			},
			type: "bar",
			colors: ["#e05c5c"],
			axisOptions: {
				yAxisMode: "tick",
				xIsSeries: true,
			},
			tooltipOptions: {
				formatTooltipY: (value) =>
					symbol + " " + format_number(value, null, 2),
			},
			barOptions: {
				spaceRatio: 0.4,
			},
			height: 260,
			title: __("Outstanding by Aging Bucket") + (currency ? ` (${currency})` : ""),
		};
	},

	onload: function (report) {
		// Shortcut to summary report
		report.page.add_inner_button(__("AP Summary"), function () {
			var filters = report.get_values();
			frappe.set_route("query-report", "Accounts Payable Summary", {
				company: filters.company,
			});
		});
	},
};

// ── Helper: inject badge / bucket styles once ─────────────────────────────────
function inject_ap_styles() {
	if (document.getElementById("ap-aging-styles")) return;

	const style = document.createElement("style");
	style.id = "ap-aging-styles";
	style.textContent = `
		/* Status badges */
		.ap-badge {
			display: inline-block;
			padding: 2px 9px;
			border-radius: 20px;
			font-size: 11px;
			font-weight: 600;
			letter-spacing: 0.03em;
			text-transform: uppercase;
		}
		.ap-badge--overdue {
			background: #fde8e8;
			color: #c0392b;
			border: 1px solid #f5b7b1;
		}
		.ap-badge--current {
			background: #e8f8f0;
			color: #1e8449;
			border: 1px solid #a9dfbf;
		}

		/* Aging bucket pills */
		.ap-bucket {
			display: inline-block;
			padding: 2px 8px;
			border-radius: 4px;
			font-size: 11px;
			font-weight: 600;
			font-family: monospace;
		}
		.bucket-0 { background: #eafaf1; color: #1e8449; }
		.bucket-1 { background: #fef9e7; color: #b7950b; }
		.bucket-2 { background: #fef0e7; color: #ca6f1e; }
		.bucket-3 { background: #fde8e8; color: #c0392b; }
		.bucket-4 { background: #f4ecf7; color: #7d3c98; }

		/* Right-align currency cells */
		.dt-cell--currency { text-align: right !important; }
	`;
	document.head.appendChild(style);
}

// ── Utility: format a number as currency string with symbol ───────────────────
function format_currency(value, currency) {
	const symbol = frappe.get_currency_symbol
		? (frappe.get_currency_symbol(currency) || currency)
		: currency;
	const num = flt(value).toLocaleString("en-US", {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
	return `${symbol} ${num}`;
}