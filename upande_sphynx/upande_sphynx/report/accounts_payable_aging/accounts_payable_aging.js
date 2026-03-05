// Copyright (c) 2026, Jeniffer and contributors
// For license information, please see license.tx

// Copyright (c) 2024 Upande Sphynx
// Accounts Payable Aging — Script Report (JS)

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
			default:   frappe.datetime.year_start(),
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
					filters: { company, account_type: "Payable", is_group: 0 },
				};
			},
		},
		{
			fieldname: "party",
			label:     __("Supplier(s)"),
			fieldtype: "MultiSelectList",
			get_data:  (txt) => frappe.db.get_link_options("Supplier", txt),
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

		const currency_cols = [
			"grand_total", "paid_amount", "outstanding_amount",
			"range1", "range2", "range3", "range4", "range5",
		];

		if (currency_cols.includes(column.fieldname)) {
			const num = flt(value);
			if (num === 0) return `<span class="ap-zero">—</span>`;
			const symbol = get_currency_symbol(data.currency);
			const formatted = num.toLocaleString("en-US", {
				minimumFractionDigits: 2,
				maximumFractionDigits: 2,
			});
			return `<span class="ap-num">${symbol}${formatted}</span>`;
		}

		if (column.fieldname === "status") {
			return value === "Overdue"
				? `<span class="ap-badge ap-overdue">Overdue</span>`
				: `<span class="ap-badge ap-current">Current</span>`;
		}

		if (column.fieldname === "aging_bucket") {
			const cls = { "0-30":"ap-b0","31-60":"ap-b1","61-90":"ap-b2","91-120":"ap-b3","121+":"ap-b4" }[value] || "ap-b0";
			return `<span class="ap-bucket ${cls}">${value}</span>`;
		}

		if (data.bold) {
			return `<strong>${default_formatter(value, row, column, data)}</strong>`;
		}

		return default_formatter(value, row, column, data);
	},

	// ── Chart ─────────────────────────────────────────────────────────────────
	get_chart_data: function (columns, result) {
		if (!result || !result.length) return;

		const fields = ["range1","range2","range3","range4","range5"];
		const labels = ["0-30","31-60","61-90","91-120","121+"];
		const totals = [0,0,0,0,0];
		let currency = "";

		result.forEach((row) => {
			if (!row.invoice_no) return;
			if (!currency && row.currency) currency = row.currency;
			fields.forEach((f, i) => { totals[i] += flt(row[f]); });
		});

		const symbol = get_currency_symbol(currency);

		return {
			data: { labels, datasets: [{ name: __("Outstanding"), values: totals }] },
			type:   "bar",
			colors: ["#e05c5c"],
			height: 240,
			axisOptions: { xIsSeries: true },
			tooltipOptions: {
				formatTooltipY: (v) => symbol + Number(v).toLocaleString("en-US", {
					minimumFractionDigits: 2, maximumFractionDigits: 2,
				}),
			},
			title: __("Outstanding by Aging Bucket") + (currency ? ` (${symbol})` : ""),
		};
	},

	// ── Toolbar ───────────────────────────────────────────────────────────────
// 	onload: function (report) {
// 		inject_ap_styles();

// 		// Instead of linking to the standard AP Summary (which shows Shareholders
// 		// and payment entries), we open the standard report but immediately
// 		// patch its "Accounts Payable" back-button to return here.
// 		report.page.add_inner_button(__("AP Summary"), function () {
// 			const f = report.get_values();

// 			// Store a flag so we can detect we came from here
// 			frappe.route_flags = frappe.route_flags || {};
// 			frappe.route_flags.ap_aging_origin = true;

// 			frappe.set_route("query-report", "Accounts Payable Summary", {
// 				company: f.company,
// 			});
// 		});
// 	},

// 	after_datatable_render: function () {
// 		inject_ap_styles();
// 		patch_ap_summary_back_button();
// 	},
// };

// // ── Patch AP Summary back-button ──────────────────────────────────────────────
// // Called after every render. When we are ON the AP Summary page and we
// // arrived from our custom report, replace the "Accounts Payable" toolbar
// // button so it redirects back to "Accounts Payable Aging".
// function patch_ap_summary_back_button() {
// 	const route = frappe.get_route();
// 	if (!route || route[1] !== "Accounts Payable Summary") return;
// 	if (!frappe.route_flags || !frappe.route_flags.ap_aging_origin) return;

// 	// Give the DOM a moment to render the toolbar buttons
// 	setTimeout(() => {
// 		$(".page-head .inner-toolbar .btn, .page-head .custom-btn-group .btn")
// 			.filter(function () {
// 				return $(this).text().trim() === __("Accounts Payable");
// 			})
// 			.each(function () {
// 				$(this)
// 					.text(__("← AP Aging"))
// 					.off("click.ap_patch")
// 					.on("click.ap_patch", function (e) {
// 						e.preventDefault();
// 						frappe.route_flags.ap_aging_origin = false;
// 						frappe.set_route("query-report", "Accounts Payable Aging");
// 					});
// 			});
// 	}, 600);
// }

// // Also run the patch whenever the page renders (catches navigation from
// // AP Summary button in the toolbar)
// $(document).on("page-change", function () {
// 	setTimeout(patch_ap_summary_back_button, 700);
// });

// ── Currency symbol lookup ────────────────────────────────────────────────────
const SYMBOL_FALLBACK = {
	USD:"$",   EUR:"€",   GBP:"£",   JPY:"¥",   CNY:"¥",
	INR:"₹",   KES:"KSh", UGX:"USh", TZS:"TSh", ZAR:"R",
	AUD:"A$",  CAD:"C$",  CHF:"Fr",  SGD:"S$",  AED:"د.إ",
	NGN:"₦",   GHS:"₵",   RWF:"FRw", ETB:"Br",  MXN:"$",
	BRL:"R$",  SEK:"kr",  NOK:"kr",  DKK:"kr",
};

function get_currency_symbol(code) {
	if (!code) return "";

	// 1. frappe.boot.currency_symbols — set at login, most reliable
	const boot = frappe.boot && frappe.boot.currency_symbols;
	if (boot && boot[code]) return boot[code];

	// 2. frappe helper — only trust if it returns something other than the code
	if (frappe.get_currency_symbol) {
		const s = frappe.get_currency_symbol(code);
		if (s && s !== code) return s;
	}

	// 3. Hardcoded fallback
	return SYMBOL_FALLBACK[code] || code;
}

// ── Styles ────────────────────────────────────────────────────────────────────
function inject_ap_styles() {
	if (document.getElementById("ap-aging-styles")) return;
	const s = document.createElement("style");
	s.id = "ap-aging-styles";
	s.textContent = `
		.ap-num  { display:block; text-align:right; font-variant-numeric:tabular-nums; }
		.ap-zero { display:block; text-align:right; color:#bbb; }
		.ap-badge {
			display:inline-block; padding:2px 9px; border-radius:20px;
			font-size:11px; font-weight:600; letter-spacing:.04em; text-transform:uppercase;
		}
		.ap-overdue { background:#fde8e8; color:#a02020; border:1px solid #f5b7b1; }
		.ap-current { background:#eafaf1; color:#1e6b3a; border:1px solid #a9dfbf; }
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
