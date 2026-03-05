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

		// ── Currency columns: symbol + 2 d.p., never raw float ────────────────
		const currency_cols = [
			"outstanding_amount",
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

		// ── Status badge ───────────────────────────────────────────────────────
		if (column.fieldname === "status") {
			if (value === "Overdue") {
				return `<span class="ap-badge ap-overdue">
							<span class="ap-badge-dot"></span>Overdue
						</span>`;
			}
			return `<span class="ap-badge ap-current">
						<span class="ap-badge-dot"></span>Current
					</span>`;
		}

		// ── Aging bucket pill ──────────────────────────────────────────────────
		if (column.fieldname === "aging_bucket") {
			const meta = {
				"0-30":   { cls: "ap-b0", icon: "●" },
				"31-60":  { cls: "ap-b1", icon: "●" },
				"61-90":  { cls: "ap-b2", icon: "●" },
				"91-120": { cls: "ap-b3", icon: "●" },
				"121+":   { cls: "ap-b4", icon: "●" },
			}[value] || { cls: "ap-b0", icon: "●" };
			return `<span class="ap-bucket ${meta.cls}">${value}</span>`;
		}

		// ── Bold for summary / total rows ──────────────────────────────────────
		if (data.bold) {
			return `<strong>${default_formatter(value, row, column, data)}</strong>`;
		}

		return default_formatter(value, row, column, data);
	},

	// ── Chart ─────────────────────────────────────────────────────────────────
	get_chart_data: function (columns, result) {
		if (!result || !result.length) return;

		const fields  = ["range1", "range2", "range3", "range4", "range5"];
		const labels  = ["0–30", "31–60", "61–90", "91–120", "121+"];
		const totals  = [0, 0, 0, 0, 0];
		let currency  = "";

		result.forEach((row) => {
			if (!row.invoice_no) return;                  // skip blank / total rows
			if (!currency && row.currency) currency = row.currency;
			fields.forEach((f, i) => { totals[i] += flt(row[f]); });
		});

		const symbol = get_currency_symbol(currency);

		return {
			data: {
				labels,
				datasets: [{
					name:   __("Outstanding"),
					values: totals,
				}],
			},
			type:   "bar",
			// Gradient from green (current) to deep purple (very overdue)
			colors: ["#27ae60", "#f39c12", "#e67e22", "#e74c3c", "#8e44ad"],
			barOptions: { stacked: false, spaceRatio: 0.35 },
			height: 260,
			axisOptions: { xIsSeries: true },
			tooltipOptions: {
				formatTooltipY: (v) =>
					symbol + Number(v).toLocaleString("en-US", {
						minimumFractionDigits: 2,
						maximumFractionDigits: 2,
					}),
			},
			title: __("Outstanding by Aging Bucket") +
				   (currency ? `  (${symbol} ${currency})` : ""),
		};
	},

	// ── On load ───────────────────────────────────────────────────────────────
	onload: function (report) {
		inject_ap_styles();
	},

	after_datatable_render: function () {
		inject_ap_styles();
	},
};

// ── Currency symbol lookup ─────────────────────────────────────────────────────
// Three-tier: boot object → frappe helper → hardcoded map → code fallback
const SYMBOL_FALLBACK = {
	USD: "$",    EUR: "€",    GBP: "£",    JPY: "¥",    CNY: "¥",
	INR: "₹",    KES: "KSh",  UGX: "USh",  TZS: "TSh",  ZAR: "R",
	AUD: "A$",   CAD: "C$",   CHF: "Fr",   SGD: "S$",   AED: "د.إ",
	NGN: "₦",    GHS: "₵",    RWF: "FRw",  ETB: "Br",   MXN: "$",
	BRL: "R$",   SEK: "kr",   NOK: "kr",   DKK: "kr",   HUF: "Ft",
	PLN: "zł",   CZK: "Kč",   RON: "lei",  HKD: "HK$",  NZD: "NZ$",
};

function get_currency_symbol(code) {
	if (!code) return "";

	// 1. Boot map — most reliable, populated at login
	const boot = frappe.boot && frappe.boot.currency_symbols;
	if (boot && boot[code]) return boot[code];

	// 2. Frappe helper — only use if it returns something other than the code itself
	if (typeof frappe.get_currency_symbol === "function") {
		const s = frappe.get_currency_symbol(code);
		if (s && s !== code) return s;
	}

	// 3. Hardcoded fallback map
	return SYMBOL_FALLBACK[code] || code;
}

// ── Styles ────────────────────────────────────────────────────────────────────
function inject_ap_styles() {
	if (document.getElementById("ap-aging-styles")) return;

	const s = document.createElement("style");
	s.id    = "ap-aging-styles";
	s.textContent = `
		/* ── Numbers ──────────────────────────────────────────────────────── */
		.ap-num {
			display: block;
			text-align: right;
			font-variant-numeric: tabular-nums;
			font-size: 12.5px;
			letter-spacing: 0.01em;
		}
		.ap-zero {
			display: block;
			text-align: right;
			color: #c8c4bc;
			font-size: 13px;
		}

		/* ── Status badges ────────────────────────────────────────────────── */
		.ap-badge {
			display: inline-flex;
			align-items: center;
			gap: 5px;
			padding: 3px 10px 3px 7px;
			border-radius: 20px;
			font-size: 11px;
			font-weight: 600;
			letter-spacing: 0.05em;
			text-transform: uppercase;
			white-space: nowrap;
		}
		.ap-badge-dot {
			width: 6px;
			height: 6px;
			border-radius: 50%;
			flex-shrink: 0;
		}
		.ap-overdue {
			background: #fdf0f0;
			color: #b91c1c;
			border: 1px solid #fca5a5;
		}
		.ap-overdue .ap-badge-dot { background: #ef4444; }

		.ap-current {
			background: #f0fdf4;
			color: #15803d;
			border: 1px solid #86efac;
		}
		.ap-current .ap-badge-dot { background: #22c55e; }

		/* ── Aging bucket pills ───────────────────────────────────────────── */
		.ap-bucket {
			display: inline-block;
			padding: 3px 9px;
			border-radius: 5px;
			font-size: 11.5px;
			font-weight: 700;
			font-family: 'Courier New', monospace;
			letter-spacing: 0.03em;
			white-space: nowrap;
		}
		.ap-b0 {
			background: #f0fdf4;
			color: #166534;
			border: 1px solid #bbf7d0;
		}
		.ap-b1 {
			background: #fefce8;
			color: #854d0e;
			border: 1px solid #fde68a;
		}
		.ap-b2 {
			background: #fff7ed;
			color: #9a3412;
			border: 1px solid #fed7aa;
		}
		.ap-b3 {
			background: #fef2f2;
			color: #991b1b;
			border: 1px solid #fecaca;
		}
		.ap-b4 {
			background: #faf5ff;
			color: #6b21a8;
			border: 1px solid #e9d5ff;
		}

		/* ── Row hover polish ─────────────────────────────────────────────── */
		.dt-row:hover .ap-num  { color: #1c1917; }
		.dt-row:hover .ap-zero { color: #a8a29e; }
	`;
	document.head.appendChild(s);
}
