// Copyright (c) 2025, Jeniffer and contributors
// For license information, please see license.txt

// Reminds the user this record doesn't affect the books on its own — a
// Share Movement is just a record of shares changing hands until it's
// submitted and, for anything other than an Opening Entry, has a Journal
// Entry created from it.
frappe.ui.form.on('Share Movement', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0 && !frm.doc.__islocal) {
            frm.set_intro(__('This Share Movement is still a Draft. Submit it to make it official, then use "Create Journal Entry" (once submitted) to record the accounting impact on your books.'), 'orange');
        } else if (frm.doc.docstatus === 1 && !frm.doc.journal_entry_ref && frm.doc.is_opening_entry !== 'Yes') {
            frm.set_intro(__('Submitted. Use the "Create Journal Entry" button above to record this in your books.'), 'blue');
        } else {
            frm.set_intro();
        }
    }
});

frappe.ui.form.on('Share Movement', {
    refresh: function(frm) {
        // Add Cancel button for submitted documents
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Cancelled') {
            frm.add_custom_button(__('Cancel Movement'), function() {
                frappe.confirm(
                    __('This will cancel this Share Movement and linked Journal Entry. Continue?'),
                    function() {
                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.cancel_share_movement',
                            args: {
                                share_movement_name: frm.doc.name
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
            frm.add_custom_button(__('Delete Movement'), function() {
                frappe.confirm(
                    __('This will permanently delete this Share Movement and linked Journal Entry. This cannot be undone. Continue?'),
                    function() {
                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.delete_share_movement',
                            args: {
                                share_movement_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Deleting documents...'),
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.msgprint(__('Documents deleted successfully'));
                                    frappe.set_route('List', 'Share Movement');
                                }
                            }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-danger');
        }
    }
});

// Migrated from the site's "Share Movement Calc" Client Script.
frappe.ui.form.on('Share Movement', {
    refresh: function(frm) {
        if (frm.doc.company && !frm.doc.base_currency) {
            frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
                if (r && r.default_currency) {
                    frm.set_value('base_currency', r.default_currency);
                }
            });
        }

        // Create Journal Entry (only after submit, if not created, and not an opening entry)
        if (frm.doc.docstatus === 1 && !frm.doc.journal_entry_ref && frm.doc.is_opening_entry !== 'Yes') {
            let payment_required_types = [
                'Equity Capital Injection',
                'Share Purchase',
                'Loan Equity Injection',
                'Share Buyback'
            ];

            if (payment_required_types.includes(frm.doc.movement_type)) {
                frm.add_custom_button(__('Create Journal Entry'), function() {
                    if (!frm.doc.bank_account || !frm.doc.payment_date) {
                        let prompt_fields = [];

                        if (!frm.doc.bank_account) {
                            prompt_fields.push({
                                fieldname: 'bank_account',
                                label: __('Bank Account'),
                                fieldtype: 'Link',
                                options: 'Bank Account',
                                reqd: 1,
                                get_query: function() {
                                    return {
                                        filters: {
                                            'company': frm.doc.company,
                                            'is_company_account': 1
                                        }
                                    };
                                }
                            });
                        }

                        if (!frm.doc.payment_date) {
                            prompt_fields.push({
                                fieldname: 'payment_date',
                                label: __('Payment Date'),
                                fieldtype: 'Date',
                                default: frm.doc.transaction_date,
                                reqd: 1
                            });
                        }

                        prompt_fields.push({
                            fieldname: 'payment_reference',
                            label: __('Payment Reference'),
                            fieldtype: 'Data',
                            description: __('Cheque number, wire transfer reference, etc.'),
                            reqd: 1
                        });

                        frappe.prompt(prompt_fields, function(values) {
                            if (values.bank_account) {
                                frm.doc.bank_account = values.bank_account;
                            }
                            if (values.payment_date) {
                                frm.doc.payment_date = values.payment_date;
                            }
                            if (values.payment_reference) {
                                frm.doc.payment_reference = values.payment_reference;
                            }

                            frm.save('Update', function() {
                                create_share_movement_journal_entry(frm);
                            });
                        }, __('Payment Details'), __('Create Journal Entry'));
                    } else {
                        create_share_movement_journal_entry(frm);
                    }
                }, __('Actions'));
            }
        }

        if (frm.doc.to_shareholder) {
            frm.add_custom_button(__('View Shareholder Holdings'), function() {
                frappe.route_options = {
                    "shareholder": frm.doc.to_shareholder
                };
                frappe.set_route("query-report", "Share Transactions Report");
            }, __('View'));
        }
    },

    number_of_shares: function(frm) {
        calculate_share_movement_amounts(frm);
    },

    price_per_share: function(frm) {
        calculate_share_movement_amounts(frm);
    },

    par_value_per_share: function(frm) {
        calculate_share_movement_amounts(frm);
    },

    transaction_currency: function(frm) {
        fetch_share_movement_exchange_rate(frm);
    },

    exchange_rate: function(frm) {
        calculate_share_movement_base_amount(frm);
    },

    company: function(frm) {
        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
                if (r && r.default_currency) {
                    frm.set_value('base_currency', r.default_currency);
                    fetch_share_movement_exchange_rate(frm);
                }
            });
        }
        setup_share_movement_filters(frm);
        frm.set_value('share_capital_account', '');
        frm.set_value('share_premium_account', '');
        frm.set_value('bank_account', '');
    }
});

function calculate_share_movement_amounts(frm) {
    if (frm.doc.number_of_shares && frm.doc.price_per_share && frm.doc.par_value_per_share) {
        let total = frm.doc.number_of_shares * frm.doc.price_per_share;
        frm.set_value('total_amount', total);

        let capital = frm.doc.number_of_shares * frm.doc.par_value_per_share;
        let premium = total - capital;

        frm.set_value('share_capital_amount', capital);
        frm.set_value('share_premium_amount', premium);

        calculate_share_movement_base_amount(frm);
    }
}

function calculate_share_movement_base_amount(frm) {
    if (frm.doc.total_amount && frm.doc.exchange_rate) {
        let base_amount = frm.doc.total_amount * frm.doc.exchange_rate;
        frm.set_value('total_amount_base_currency', base_amount);
    }
}

function fetch_share_movement_exchange_rate(frm) {
    if (frm.doc.transaction_currency && frm.doc.base_currency) {
        if (frm.doc.transaction_currency === frm.doc.base_currency) {
            frm.set_value('exchange_rate', 1.0);
            return;
        }

        frappe.call({
            method: 'erpnext.setup.utils.get_exchange_rate',
            args: {
                from_currency: frm.doc.transaction_currency,
                to_currency: frm.doc.base_currency,
                transaction_date: frm.doc.transaction_date || frappe.datetime.get_today()
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('exchange_rate', r.message);
                }
            }
        });
    }
}

function create_share_movement_journal_entry(frm) {
    frappe.confirm(
        'Create Journal Entry for ' + format_currency(frm.doc.total_amount, frm.doc.transaction_currency) + '?',
        function() {
            frappe.call({
                method: 'upande_sphynx.api.capital_management.create_journal_entry_from_share_movement',
                args: {
                    share_movement_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Creating Journal Entry...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Journal Entry {0} created successfully', [r.message]),
                            indicator: 'green'
                        }, 5);
                        frm.reload_doc();

                        frappe.msgprint({
                            title: __('Journal Entry Created'),
                            message: __('Journal Entry {0} has been created and submitted.', [r.message]),
                            primary_action: {
                                label: __('Open Journal Entry'),
                                action: function() {
                                    frappe.set_route('Form', 'Journal Entry', r.message);
                                }
                            }
                        });
                    }
                }
            });
        }
    );
}

// Migrated from the site's "Share Movement Account Filters" Client Script.
frappe.ui.form.on('Share Movement', {
    refresh: function(frm) {
        setup_share_movement_filters(frm);
    }
});

function setup_share_movement_filters(frm) {
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

