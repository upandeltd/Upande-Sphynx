// Consolidated client script for Share Transfer.
//
// Rebuilt to match what is actually live in production: two Client Scripts
// ("Currency Share Management" and "Share Management"). An earlier version
// of this file was built against 9 experimental scripts sitting on a dev
// site that turned out not to reflect production at all — this replaces
// that mistake.
//
// Note: production's two live scripts disagreed with each other on the
// `share_capital_account` filter (one allowed Liability only, the other
// allowed Equity or Liability) and on how the `rate` field is derived
// (divide vs. multiply by exchange rate, vs. leaving it unconverted). This
// file resolves both by matching server-side validation/calculation
// (Equity-or-Liability, and rate = rate_in_transaction_currency * exchange_rate,
// i.e. company-currency semantics) rather than either ambiguous client-only
// version — see the "Fixed" changelog in the SOP for details.

frappe.ui.form.on('Share Transfer', {
	onload: function (frm) {
		if (frm.is_new() && !frm.doc.transaction_currency && frm.doc.company) {
			frappe.db.get_value('Company', frm.doc.company, 'default_currency', (r) => {
				if (r && r.default_currency) {
					frm.set_value('transaction_currency', r.default_currency);
				}
			});
		}
		set_account_filters(frm);
	},

	refresh: function (frm) {
		set_account_filters(frm);

		frm.remove_custom_button('Create Journal Entry');
		frm.remove_custom_button('Create Multi-Currency Journal Entry');
		frm.remove_custom_button('View Journal Entry');
		frm.remove_custom_button('Cancel Journal Entry');

		if (frm.doc.docstatus === 1 && !frm.doc.custom_journal_entry) {
			frm.add_custom_button(__('Create Multi-Currency Journal Entry'), () => create_journal_entry(frm));
			frm.page.set_primary_action(__('Create Journal Entry'), () => create_journal_entry(frm));
		}

		if (frm.doc.custom_journal_entry) {
			frm.add_custom_button(__('View Journal Entry'), () => {
				frappe.set_route('Form', 'Journal Entry', frm.doc.custom_journal_entry);
			}, __('View'));
			frm.dashboard.add_indicator(__('Journal Entry Created: {0}', [frm.doc.custom_journal_entry]), 'green');

			if (frm.doc.docstatus === 1) {
				frm.add_custom_button(__('Cancel Journal Entry'), () => {
					frappe.confirm(__('Cancel Journal Entry {0}?', [frm.doc.custom_journal_entry]), () => {
						frappe.call({
							method: 'upande_sphynx.share_transfer_customization.share_transfer_controller.cancel_custom_journal_entry',
							args: { docname: frm.doc.name },
							freeze: true,
							freeze_message: __('Cancelling Journal Entry...'),
							callback: function (r) {
								if (!r.exc) {
									frm.reload_doc();
								}
							},
						});
					});
				}, __('Actions'));
			}
		}
	},

	company: function (frm) {
		if (frm.doc.company && !frm.doc.transaction_currency) {
			frappe.db.get_value('Company', frm.doc.company, 'default_currency', (r) => {
				if (r && r.default_currency) {
					frm.set_value('transaction_currency', r.default_currency);
				}
			});
		}
		set_account_filters(frm);
	},

	transaction_currency: function (frm) {
		handle_currency_change(frm);
		set_account_filters(frm);
		calculate_total_amount(frm);
	},

	exchange_rate: function (frm) {
		calculate_amounts(frm);
	},

	no_of_shares: function (frm) {
		calculate_total_amount(frm);
	},

	rate_in_transaction_currency: function (frm) {
		calculate_total_amount(frm);
	},
});

function set_account_filters(frm) {
	if (!frm.doc.company) {
		return;
	}
	const currency_filter = frm.doc.transaction_currency ? { account_currency: frm.doc.transaction_currency } : {};

	frm.set_query('share_capital_account', () => ({
		filters: Object.assign(
			{ company: frm.doc.company, is_group: 0, root_type: ['in', ['Equity', 'Liability']] },
			currency_filter
		),
	}));

	frm.set_query('receiving_account', () => ({
		filters: Object.assign(
			{ company: frm.doc.company, is_group: 0, account_type: ['in', ['Bank', 'Cash']] },
			currency_filter
		),
	}));

	frm.set_query('cost_center', () => ({
		filters: { company: frm.doc.company, is_group: 0 },
	}));
}

function handle_currency_change(frm) {
	if (!frm.doc.transaction_currency || !frm.doc.company) {
		return;
	}
	frappe.db.get_value('Company', frm.doc.company, 'default_currency', (r) => {
		if (!r || !r.default_currency) {
			return;
		}
		const company_currency = r.default_currency;

		if (frm.doc.transaction_currency !== company_currency) {
			frm.set_df_property('exchange_rate', 'reqd', 1);
			frm.set_df_property('exchange_rate', 'hidden', 0);
			if (!frm.doc.exchange_rate) {
				fetch_exchange_rate(frm, frm.doc.transaction_currency, company_currency);
			}
		} else {
			frm.set_value('exchange_rate', 1);
			frm.set_df_property('exchange_rate', 'reqd', 0);
			frm.set_df_property('exchange_rate', 'hidden', 1);
		}
	});
}

function fetch_exchange_rate(frm, from_currency, to_currency) {
	frappe.call({
		method: 'erpnext.setup.utils.get_exchange_rate',
		args: {
			from_currency: from_currency,
			to_currency: to_currency,
			transaction_date: frm.doc.date || frappe.datetime.get_today(),
		},
		callback: function (r) {
			if (r.message) {
				frm.set_value('exchange_rate', r.message);
			}
		},
	});
}

function calculate_total_amount(frm) {
	if (frm.doc.no_of_shares && frm.doc.rate_in_transaction_currency) {
		const total = flt(frm.doc.no_of_shares) * flt(frm.doc.rate_in_transaction_currency);
		frm.set_value('total_amount_in_transaction_currency', total);
	}
	calculate_amounts(frm);
}

function calculate_amounts(frm) {
	const exchange_rate = frm.doc.exchange_rate || 1;
	if (frm.doc.rate_in_transaction_currency) {
		frm.set_value('rate', flt(frm.doc.rate_in_transaction_currency) * exchange_rate);
	}
	if (frm.doc.total_amount_in_transaction_currency) {
		const company_amount = flt(frm.doc.total_amount_in_transaction_currency) * exchange_rate;
		frm.set_value('total_amount_in_company_currency', company_amount);
		frm.set_value('amount', company_amount);
	}
}

function create_journal_entry(frm) {
	if (!frm.doc.share_capital_account) {
		frappe.msgprint({
			title: __('Missing Account'),
			indicator: 'red',
			message: __('Please set Share Capital Account (Equity/Liability) before creating journal entry'),
		});
		return;
	}
	if (!frm.doc.receiving_account) {
		frappe.msgprint({
			title: __('Missing Account'),
			indicator: 'red',
			message: __('Please set Receiving Account (Asset) before creating journal entry'),
		});
		return;
	}
	if (!frm.doc.total_amount_in_transaction_currency || frm.doc.total_amount_in_transaction_currency <= 0) {
		frappe.msgprint({
			title: __('Invalid Amount'),
			indicator: 'red',
			message: __('Please ensure the total amount is greater than zero'),
		});
		return;
	}

	const confirmation_message = __(
		'Are you sure you want to create a Journal Entry for this Share Transfer?<br><br>' +
			'<b>Transaction:</b> {0} shares @ {1} {2} per share<br>' +
			'<b>Total Amount:</b> {3} {4}<br>' +
			'<b>Debit (Receiving):</b> {5}<br>' +
			'<b>Credit (Share Capital):</b> {6}',
		[
			frm.doc.no_of_shares,
			format_currency(frm.doc.rate_in_transaction_currency, frm.doc.transaction_currency),
			frm.doc.transaction_currency,
			format_currency(frm.doc.total_amount_in_transaction_currency, frm.doc.transaction_currency),
			frm.doc.transaction_currency,
			frm.doc.receiving_account,
			frm.doc.share_capital_account,
		]
	);

	frappe.confirm(confirmation_message, function () {
		frappe.call({
			method: 'upande_sphynx.share_transfer_customization.share_transfer_controller.create_custom_journal_entry',
			args: { docname: frm.doc.name },
			freeze: true,
			freeze_message: __('Creating Journal Entry...'),
			callback: function (r) {
				if (!r.exc && r.message && r.message.journal_entry) {
					frappe.show_alert({
						message: __('Journal Entry {0} created successfully', [r.message.journal_entry]),
						indicator: 'green',
					}, 5);
					frm.reload_doc();
				}
			},
		});
	});
}
