// Copyright (c) 2025, Jeniffer and contributors
// For license information, please see license.txt

frappe.ui.form.on('Share Agreement', {
    refresh: function(frm) {
        // Add Cancel button for submitted documents
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Cancelled') {
            frm.add_custom_button(__('Cancel Agreement'), function() {
                frappe.confirm(
                    __('This will cancel this Share Agreement and all linked documents (Share Movement, Journal Entries). Continue?'),
                    function() {
                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.cancel_share_agreement',
                            args: {
                                share_agreement_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Cancelling documents...'),
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.msgprint(__('Documents cancelled successfully'));
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }

        // Add Delete button for cancelled documents
        if (frm.doc.docstatus === 2) {
            frm.add_custom_button(__('Delete Agreement'), function() {
                frappe.confirm(
                    __('This will permanently delete this Share Agreement and all linked documents. This cannot be undone. Continue?'),
                    function() {
                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.delete_share_agreement',
                            args: {
                                share_agreement_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Deleting documents...'),
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.msgprint(__('Documents deleted successfully'));
                                    frappe.set_route('List', 'Share Agreement');
                                }
                            }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-danger');
        }
    }
});

// Migrated from the site's "Share Agreement Buttons" Client Script.
frappe.ui.form.on('Share Agreement', {
    refresh: function(frm) {
        // Issue Shares (creates Share Movement, not JE)
        if (frm.doc.docstatus === 1 && !frm.doc.share_movement_ref) {
            frm.add_custom_button(__('Issue Shares'), function() {
                frappe.confirm(
                    'Issue ' + frm.doc.number_of_shares + ' shares to ' + frm.doc.shareholder + '?<br><br>' +
                    '<small>This will create a Share Movement. You can create the Journal Entry for payment from the Share Movement.</small>',
                    function() {
                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.issue_shares_from_agreement',
                            args: {
                                share_agreement_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Creating Share Movement...'),
                            callback: function(r) {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __('Share Movement {0} created successfully', [r.message]),
                                        indicator: 'green'
                                    }, 5);
                                    frappe.set_route('Form', 'Share Movement', r.message);
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }
    },

    number_of_shares: function(frm) {
        calculate_agreement_amounts(frm);
    },

    rate_per_share: function(frm) {
        calculate_agreement_amounts(frm);
    },

    par_value_per_share: function(frm) {
        calculate_agreement_amounts(frm);
    },

    company: function(frm) {
        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
                if (r && r.default_currency && frm.doc.transaction_currency &&
                    frm.doc.transaction_currency !== r.default_currency) {
                    fetch_agreement_exchange_rate(frm, r.default_currency);
                }
            });
        }
        setup_share_agreement_filters(frm);
        frm.set_value('share_capital_account', '');
        frm.set_value('share_premium_account', '');
        frm.set_value('bank_account', '');
    },

    transaction_currency: function(frm) {
        if (frm.doc.company && frm.doc.transaction_currency) {
            frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
                if (r && r.default_currency) {
                    fetch_agreement_exchange_rate(frm, r.default_currency);
                }
            });
        }
    }
});

function calculate_agreement_amounts(frm) {
    if (frm.doc.number_of_shares && frm.doc.rate_per_share && frm.doc.par_value_per_share) {
        let total = frm.doc.number_of_shares * frm.doc.rate_per_share;
        let capital = frm.doc.number_of_shares * frm.doc.par_value_per_share;
        let premium = total - capital;

        frm.set_value('total_consideration', total);
        frm.set_value('premium_amount', premium);
    }
}

function fetch_agreement_exchange_rate(frm, base_currency) {
    if (frm.doc.transaction_currency === base_currency) {
        frm.set_value('exchange_rate', 1.0);
        return;
    }

    frappe.call({
        method: 'erpnext.setup.utils.get_exchange_rate',
        args: {
            from_currency: frm.doc.transaction_currency,
            to_currency: base_currency,
            transaction_date: frm.doc.agreement_date || frappe.datetime.get_today()
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('exchange_rate', r.message);
            }
        }
    });
}

// Migrated from the site's "Share Agreement Account Filters" Client Script.
frappe.ui.form.on('Share Agreement', {
    refresh: function(frm) {
        setup_share_agreement_filters(frm);
    }
});

function setup_share_agreement_filters(frm) {
    if (frm.doc.company) {
        frm.set_query('share_capital_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'account_type': 'Equity',
                    'is_group': 0
                }
            };
        });

        frm.set_query('share_premium_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'account_type': 'Equity',
                    'is_group': 0
                }
            };
        });

        frm.set_query('bank_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'is_company_account': 1
                }
            };
        });
    }
}