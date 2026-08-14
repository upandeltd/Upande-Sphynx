frappe.ui.form.on('Shareholder', {
	refresh: function (frm) {
		if (frm.doc.__islocal) {
			return;
		}

		frm.add_custom_button(__('Sync Totals'), function () {
			frappe.call({
				method: 'upande_sphynx.api.capital_management.recompute_shareholder_totals',
				args: {
					shareholder_name: frm.doc.name,
				},
				freeze: true,
				freeze_message: __('Recalculating Shares Held and Investment...'),
				callback: function (r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __('Totals recalculated from submitted Share Movements and active loans.'),
							indicator: 'green',
						});
						frm.reload_doc();
					}
				},
			});
		}, __('Actions'));

		frm.add_custom_button(__('View Ledger'), function () {
			frappe.route_options = {
				shareholder: frm.doc.name,
			};
			frappe.set_route('query-report', 'Share Transactions Report');
		}, __('View'));
	},
});
