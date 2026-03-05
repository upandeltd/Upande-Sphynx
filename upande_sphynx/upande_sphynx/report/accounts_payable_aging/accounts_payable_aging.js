// Copyright (c) 2026, Jeniffer and contributors
// For license information, please see license.tx

frappe.query_reports["Accounts Payable Aging"] = {

	// ── Filters ───────────────────────────────────────────────────────────────
	filters: [
		{
			fieldname: "company",
			label:     __("Company"),
			fieldtype: "Link",
			options:   "Company",
			reqd:      1,
			default:   frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label:     __("From Date"),
			fieldtype: "Date",
			reqd:      1,
			default:   frappe.datetime.year_start(),   // 1 Jan of current year
		},
		{
			fieldname: "to_date",
			label:     __("To Date"),
			fieldtype: "Date",
			reqd:      1,
			default:   frappe.datetime.get_today(),
		},
		{
			fieldname: "party_account",
			label:     __("Payable Account"),
			fieldtype: "Link",
			options:   "Account",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company:      company,
						account_type: "Payable",
						is_group:     0,
					},
				};
			},
		},
		{
			fieldname: "party",
			label:     __("Supplier(s)"),
			fieldtype: "MultiSelectList",
			get_data:  function (txt) {
				return frappe.db.get_link_options("Supplier", txt);
			},
		},
		{
			fieldname: "supplier_group",
			label:     __("Supplier Group"),
			fieldtype: "Link",
			options:   "Supplier Group",
		},
	],

	// ── Row formatter ─────────────────────────────────────────────────────────
	formatter: function (value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);

		// Currency columns — show symbol + 2dp, never a raw float
		const currency_cols = [
			"grand_total", "paid_amount", "outstanding_amount",
			"range1", "range2", "range3", "range4", "range5",
		];
		if (currency_cols.includes(column.fieldname)) {
			const num = flt(value);
			if (num === 0) return `<span class="ap-zero">—</span>`;
			const symbol = (data.currency && frappe.get_currency_symbol)
				? frappe.get_currency_symbol(data.currency)
				: (data.currency || "");
			const formatted = num.toLocaleString("en-US", {
				minimumFractionDigits: 2,
				maximumFractionDigits: 2,
			});
			return `<span class="ap-num">${symbol} ${formatted}</span>`;
		}

		// Status badge
		if (column.fieldname === "status") {
			if (value === "Overdue") {
				return `<span class="ap-badge ap-overdue">Overdue</span>`;
			}
			return `<span class="ap-badge ap-current">Current</span>`;
		}

		// Aging bucket pill
		if (column.fieldname === "aging_bucket") {
			const cls = {
				"0-30":   "ap-b0",
				"31-60":  "ap-b1",
				"61-90":  "ap-b2",
				"91-120": "ap-b3",
				"121+":   "ap-b4",
			}[value] || "ap-b0";
			return `<span class="ap-bucket ${cls}">${value}</span>`;
		}

		// Bold totals
		if (data.bold) {
			return `<strong>${default_formatter(value, row, column, data)}</strong>`;
		}

		return default_formatter(value, row, column, data);
	},

	// ── Chart ─────────────────────────────────────────────────────────────────
	get_chart_data: function (columns, result) {
		if (!result || !result.length) return;

		const fields  = ["range1", "range2", "range3", "range4", "range5"];
		const labels  = ["0-30", "31-60", "61-90", "91-120", "121+"];
		const totals  = [0, 0, 0, 0, 0];
		let currency  = "";

		result.forEach((row) => {
			if (!row.invoice_no) return;              // skip summary rows
			if (!currency && row.currency) currency = row.currency;
			fields.forEach((f, i) => { totals[i] += flt(row[f]); });
		});

		const symbol = (currency && frappe.get_currency_symbol)
			? frappe.get_currency_symbol(currency)
			: currency;

		return {
			data: {
				labels:   labels,
				datasets: [{ name: __("Outstanding"), values: totals }],
			},
			type:   "bar",
			colors: ["#e05c5c"],
			height: 240,
			axisOptions: { xIsSeries: true },
			tooltipOptions: {
				formatTooltipY: (v) =>
					symbol + " " + Number(v).toLocaleString("en-US", {
						minimumFractionDigits: 2, maximumFractionDigits: 2,
					}),
			},
			title: __("Outstanding by Aging Bucket") + (currency ? ` (${currency})` : ""),
		};
	},

	// ── Toolbar buttons ───────────────────────────────────────────────────────
	onload: function (report) {
		inject_ap_styles();

		// AP Summary button — clicking it passes current filters and adds a
		// back-link so AP Summary's "Accounts Payable" button comes back here.
		report.page.add_inner_button(__("AP Summary"), function () {
			const f = report.get_values();
			frappe.set_route("query-report", "Accounts Payable Summary", {
				company: f.company,
			});
		});

		// Override the AP Summary report's back-button label so it points
		// to this custom report instead of the default Accounts Payable.
		// We do this by monkey-patching after the route change settles.
		frappe.router.on("change", function () {
			const route = frappe.get_route();
			if (
				route[0] === "query-report" &&
				route[1] === "Accounts Payable Summary"
			) {
				setTimeout(() => {
					// Replace the built-in "Accounts Payable" button with one
					// that routes back to our custom aging report.
					const $btn = $(".page-head .inner-toolbar button")
						.filter((_, el) =>
							$(el).text().trim() === "Accounts Payable"
						);
					if ($btn.length) {
						$btn.text(__("AP Aging (Custom)")).off("click").on("click", () => {
							frappe.set_route("query-report", "Accounts Payable Aging");
						});
					}
				}, 800);
			}
		});
	},

	// Inject styles after datatable renders
	after_datatable_render: function () {
		inject_ap_styles();
	},
};

// ── Style injection (runs once) ───────────────────────────────────────────────
function inject_ap_styles() {
	if (document.getElementById("ap-aging-styles")) return;
	const s = document.createElement("style");
	s.id = "ap-aging-styles";
	s.textContent = `
		/* currency */
		.ap-num  { display:block; text-align:right; font-variant-numeric:tabular-nums; }
		.ap-zero { display:block; text-align:right; color:#bbb; }

		/* status badges */
		.ap-badge {
			display:inline-block; padding:2px 9px; border-radius:20px;
			font-size:11px; font-weight:600; letter-spacing:.04em; text-transform:uppercase;
		}
		.ap-overdue { background:#fde8e8; color:#a02020; border:1px solid #f5b7b1; }
		.ap-current { background:#eafaf1; color:#1e6b3a; border:1px solid #a9dfbf; }

		/* aging bucket pills */
		.ap-bucket {
			display:inline-block; padding:2px 8px; border-radius:4px;
			font-size:11px; font-weight:600; font-family:monospace;
		}
		.ap-b0 { background:#eafaf1; color:#1e6b3a; }
		.ap-b1 { background:#fef9e7; color:#8a6d00; }
		.ap-b2 { background:#fff3e8; color:#a04000; }
		.ap-b3 { background:#fde8e8; color:#a02020; }
		.ap-b4 { background:#f2ecf8; color:#5a2d82; }
	`;
	document.head.appendChild(s);
}
