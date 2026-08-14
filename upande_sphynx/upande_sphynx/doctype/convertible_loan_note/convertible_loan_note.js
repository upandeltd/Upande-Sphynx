// Copyright (c) 2025, Jeniffer and contributors
// For license information, please see license.txt

/// This version uses the standard cancel button
// The on_cancel hook handles everything automatically

frappe.ui.form.on('Convertible Loan Note', {
    refresh: function(frm) {
        
        // The standard Cancel button will now work
        // Your on_cancel hook clears references and cancels all linked docs
        
        // Just add a helpful message
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Cancelled') {
            frm.page.set_indicator(__('Active'), 'blue');
        }
        
        // Add Delete button for cancelled documents
        if (frm.doc.docstatus === 2) {
            frm.add_custom_button(__('Delete CLN & All Linked Docs'), function() {
                frappe.confirm(
                    __('This will PERMANENTLY delete this CLN and all linked cancelled documents. This cannot be undone!<br><br>' +
                       '<b>Are you sure?</b>'),
                    function() {
                        // Just use standard delete
                        frappe.call({
                            method: 'frappe.client.delete',
                            args: {
                                doctype: 'Convertible Loan Note',
                                name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Deleting...'),
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.show_alert({
                                        message: __('Documents deleted successfully'),
                                        indicator: 'green'
                                    });
                                    frappe.set_route('List', 'Convertible Loan Note');
                                }
                            }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-danger');
        }
    }
});

// Migrated from the site's "test date input" Client Script (the live version of
// the CLN action buttons — the separately-stored "Convertible Loan Note Buttons"
// script was an older, disabled duplicate and is not migrated).
frappe.ui.form.on('Convertible Loan Note', {
    refresh: function(frm) {
        if (frm.doc.docstatus !== 1) {
            return;
        }

        // Record Loan Disbursement
        if (!frm.doc.disbursement_journal_entry_ref && frm.doc.status === 'Draft') {
            frm.add_custom_button(__('Record Loan Disbursement'), function() {
                frappe.confirm(
                    'Record disbursement of ' + format_currency(frm.doc.principal_amount) + ' to ' + frm.doc.lender + '?',
                    function() {
                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.record_cln_disbursement',
                            args: {
                                cln_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Recording Disbursement...'),
                            callback: function(r) {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __('Journal Entry {0} created successfully', [r.message]),
                                        indicator: 'green'
                                    }, 5);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }

        // Accrue Interest
        if (frm.doc.status === 'Active') {
            frm.add_custom_button(__('Accrue Interest'), function() {
                let last_date = frm.doc.last_interest_accrual_date || frm.doc.issue_date;
                let loan_currency = frm.doc.loan_currency || 'USD';
                let company_currency = frappe.sys_defaults.currency;
                let show_exchange_rate = (loan_currency !== company_currency);

                let d = new frappe.ui.Dialog({
                    title: __('Accrue Interest'),
                    fields: [
                        {
                            label: __('Interest Period'),
                            fieldname: 'info',
                            fieldtype: 'HTML',
                            options: '<div class="alert alert-info">' +
                                '<strong>Last Accrual Date:</strong> ' + last_date + '<br>' +
                                '<strong>Principal Amount:</strong> ' + format_currency(frm.doc.principal_amount, loan_currency) + '<br>' +
                                '<strong>Interest Rate:</strong> ' + frm.doc.interest_rate + '%<br>' +
                                '<strong>Current Accrued Interest:</strong> ' + format_currency(frm.doc.accrued_interest || 0, loan_currency) +
                                '</div>'
                        },
                        {
                            label: __('Accrual Date'),
                            fieldname: 'accrual_date',
                            fieldtype: 'Date',
                            default: frappe.datetime.get_today(),
                            reqd: 1,
                            description: __('The date to post the interest journal entry')
                        },
                        {
                            label: __('Exchange Rate'),
                            fieldname: 'exchange_rate',
                            fieldtype: 'Float',
                            precision: 6,
                            default: frm.doc.exchange_rate || '',
                            description: __('Exchange rate for {0} to {1}. Leave blank to use rate from CLN or fetch current rate.',
                                [loan_currency, company_currency]),
                            hidden: !show_exchange_rate
                        }
                    ],
                    primary_action_label: __('Accrue Interest'),
                    primary_action: function(values) {
                        if (frappe.datetime.get_diff(values.accrual_date, last_date) <= 0) {
                            frappe.msgprint(__('Accrual date must be after {0}', [last_date]));
                            return;
                        }

                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.accrue_cln_interest',
                            args: {
                                cln_name: frm.doc.name,
                                accrual_date: values.accrual_date,
                                exchange_rate: values.exchange_rate || null
                            },
                            freeze: true,
                            freeze_message: __('Calculating and Recording Interest...'),
                            callback: function(r) {
                                if (r.message) {
                                    let success_msg = '<div class="interest-accrual-success">' +
                                        '<h4>Interest Accrued Successfully!</h4>' +
                                        '<table class="table table-bordered" style="margin-top: 10px;">' +
                                        '<tr><td><strong>Period:</strong></td><td>' + last_date + ' to ' + r.message.accrual_date + '</td></tr>' +
                                        '<tr><td><strong>Days:</strong></td><td>' + r.message.days_accrued + ' days</td></tr>' +
                                        '<tr><td><strong>Interest Amount:</strong></td><td>' + format_currency(r.message.interest_amount, loan_currency) + '</td></tr>';

                                    if (show_exchange_rate) {
                                        success_msg += '<tr><td><strong>Exchange Rate:</strong></td><td>' + r.message.exchange_rate_used + '</td></tr>';
                                    }

                                    success_msg += '<tr><td><strong>Total Accrued:</strong></td><td>' + format_currency(r.message.total_accrued, loan_currency) + '</td></tr>' +
                                        '<tr><td><strong>Journal Entry:</strong></td><td><a href="/app/journal-entry/' + r.message.journal_entry + '" target="_blank">' + r.message.journal_entry + '</a></td></tr>' +
                                        '</table></div>';

                                    frappe.msgprint({
                                        title: __('Interest Accrual Complete'),
                                        message: success_msg,
                                        indicator: 'green'
                                    });

                                    frm.reload_doc();
                                }
                            }
                        });

                        d.hide();
                    }
                });

                d.show();
            }, __('Actions'));
        }

        // Convert to Shares (creates Share Movement)
        if (frm.doc.status === 'Active' && !frm.doc.share_transfer_ref) {
            frm.add_custom_button(__('Convert to Shares'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Conversion Parameters'),
                    fields: [
                        {
                            label: __('Conversion Information'),
                            fieldname: 'info',
                            fieldtype: 'HTML',
                            options: '<div class="alert alert-info">' +
                                '<strong>Amount to Convert:</strong> ' + format_currency(frm.doc.principal_amount + (frm.doc.accrued_interest || 0)) + '<br>' +
                                '<strong>Discount Rate:</strong> ' + (frm.doc.conversion_discount_rate || 0) + '%<br>' +
                                '<strong>Valuation Cap:</strong> ' + (frm.doc.valuation_cap ? format_currency(frm.doc.valuation_cap) : 'Not set') +
                                '</div>'
                        },
                        {
                            label: __('Next Round Price per Share'),
                            fieldname: 'next_round_price',
                            fieldtype: 'Currency',
                            placeholder: __('Enter the price per share in the current/next funding round.')
                        },
                        {
                            label: __('Fully Diluted Shares'),
                            fieldname: 'fully_diluted_shares',
                            fieldtype: 'Int',
                            placeholder: __('Total number of shares after conversion.')
                        }
                    ],
                    primary_action_label: __('Convert'),
                    primary_action: function(values) {
                        if (!values.next_round_price && !frm.doc.valuation_cap) {
                            frappe.msgprint(__('Please provide either Next Round Price or ensure Valuation Cap is set in the CLN'));
                            return;
                        }

                        if (frm.doc.valuation_cap && !values.fully_diluted_shares) {
                            frappe.msgprint(__('Fully Diluted Shares is required when using Valuation Cap'));
                            return;
                        }

                        d.hide();

                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.convert_cln_to_shares',
                            args: {
                                cln_name: frm.doc.name,
                                next_round_price: values.next_round_price || null,
                                fully_diluted_shares: values.fully_diluted_shares || null
                            },
                            freeze: true,
                            freeze_message: __('Converting to Shares...'),
                            callback: function(r) {
                                if (r.message) {
                                    let msg = '<div class="conversion-success">' +
                                        '<h4>Conversion Successful!</h4>' +
                                        '<table class="table table-bordered">' +
                                        '<tr><td><strong>Shares Issued:</strong></td><td>' + r.message.shares_issued + '</td></tr>' +
                                        '<tr><td><strong>Conversion Price:</strong></td><td>' + format_currency(r.message.conversion_price) + '</td></tr>' +
                                        '<tr><td><strong>Total Amount:</strong></td><td>' + format_currency(r.message.total_amount) + '</td></tr>' +
                                        '<tr><td><strong>Journal Entry:</strong></td><td><a href="/app/journal-entry/' + r.message.journal_entry + '">' + r.message.journal_entry + '</a></td></tr>' +
                                        '<tr><td><strong>Share Movement:</strong></td><td><a href="/app/share-movement/' + r.message.share_movement + '">' + r.message.share_movement + '</a></td></tr>' +
                                        '</table></div>';

                                    frappe.msgprint({
                                        title: __('Conversion Complete'),
                                        message: msg,
                                        indicator: 'green'
                                    });

                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                });

                d.show();
            }, __('Actions'));
        }

        // Record Repayment (cash repayment instead of conversion)
        if (frm.doc.status === 'Active' && !frm.doc.repayment_journal_entry_ref) {
            frm.add_custom_button(__('Record Repayment'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Record Loan Repayment'),
                    fields: [
                        {
                            label: __('Repayment Summary'),
                            fieldname: 'info',
                            fieldtype: 'HTML',
                            options: '<div class="alert alert-info">' +
                                '<strong>Principal:</strong> ' + format_currency(frm.doc.principal_amount) + '<br>' +
                                '<strong>Accrued Interest:</strong> ' + format_currency(frm.doc.accrued_interest || 0) +
                                '</div>'
                        },
                        {
                            label: __('Repayment Date'),
                            fieldname: 'repayment_date',
                            fieldtype: 'Date',
                            default: frappe.datetime.get_today(),
                            reqd: 1
                        },
                        {
                            label: __('Early Repayment Penalty'),
                            fieldname: 'penalty_amount',
                            fieldtype: 'Currency',
                            hidden: !frm.doc.early_repayment_allowed,
                            description: frm.doc.early_repayment_allowed
                                ? __('Optional. Requires an Interest Expense Account to be set on this CLN.')
                                : ''
                        }
                    ],
                    primary_action_label: __('Record Repayment'),
                    primary_action: function(values) {
                        d.hide();

                        frappe.call({
                            method: 'upande_sphynx.api.capital_management.record_cln_repayment',
                            args: {
                                cln_name: frm.doc.name,
                                repayment_date: values.repayment_date,
                                penalty_amount: values.penalty_amount || null
                            },
                            freeze: true,
                            freeze_message: __('Recording Repayment...'),
                            callback: function(r) {
                                if (r.message) {
                                    let msg = '<div class="repayment-success">' +
                                        '<h4>Repayment Recorded</h4>' +
                                        '<table class="table table-bordered">' +
                                        '<tr><td><strong>Total Repaid:</strong></td><td>' + format_currency(r.message.total_repayment) + '</td></tr>' +
                                        '<tr><td><strong>Journal Entry:</strong></td><td><a href="/app/journal-entry/' + r.message.journal_entry + '">' + r.message.journal_entry + '</a></td></tr>' +
                                        '</table></div>';

                                    frappe.msgprint({
                                        title: __('Loan Repaid'),
                                        message: msg,
                                        indicator: 'green'
                                    });

                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                });

                d.show();
            }, __('Actions'));
        }
    }
});

// Auto-fetch the exchange rate on currency/company change, matching the
// convenience Share Agreement and Share Movement already had.
frappe.ui.form.on('Convertible Loan Note', {
    loan_currency: function(frm) {
        fetch_cln_exchange_rate(frm);
    },
});

function fetch_cln_exchange_rate(frm) {
    if (!frm.doc.company || !frm.doc.loan_currency) {
        return;
    }
    frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
        if (!r || !r.default_currency) {
            return;
        }
        if (frm.doc.loan_currency === r.default_currency) {
            frm.set_value('exchange_rate', 1.0);
            return;
        }
        frappe.call({
            method: 'erpnext.setup.utils.get_exchange_rate',
            args: {
                from_currency: frm.doc.loan_currency,
                to_currency: r.default_currency,
                transaction_date: frm.doc.issue_date || frappe.datetime.get_today()
            },
            callback: function(r2) {
                if (r2.message) {
                    frm.set_value('exchange_rate', r2.message);
                }
            }
        });
    });
}

// Migrated from the site's "Convertible Loan Note Account Filters" Client Script.
frappe.ui.form.on('Convertible Loan Note', {
    refresh: function(frm) {
        setup_cln_filters(frm);
    },

    company: function(frm) {
        setup_cln_filters(frm);
        fetch_cln_exchange_rate(frm);
        frm.set_value('loan_liability_account', '');
        frm.set_value('interest_expense_account', '');
        frm.set_value('interest_payable_account', '');
        frm.set_value('share_capital_account', '');
        frm.set_value('share_premium_account', '');
        frm.set_value('bank_account', '');
    },

    // Migrated from the site's "Principal == Valuation" Client Script.
    principal_amount: function(frm) {
        if (frm.doc.principal_amount && !frm.doc.valuation_cap) {
            frm.set_value('valuation_cap', frm.doc.principal_amount);
        }
    }
});

function setup_cln_filters(frm) {
    if (frm.doc.company) {
        frm.set_query('loan_liability_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'account_type': ['in', ['Liability', 'Payable']],
                    'account_currency': frm.doc.loan_currency,
                    'is_group': 0
                }
            };
        });

        frm.set_query('interest_expense_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'account_type': ['in', ['Expense Account', 'Indirect Expense']],
                    'is_group': 0
                }
            };
        });

        frm.set_query('interest_payable_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'root_type': 'Liability',
                    'account_currency': frm.doc.loan_currency,
                    'is_group': 0
                }
            };
        });

        frm.set_query('share_capital_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'account_type': 'Equity',
                    'account_currency': frm.doc.loan_currency,
                    'is_group': 0
                }
            };
        });

        frm.set_query('share_premium_account', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'account_type': 'Equity',
                    'account_currency': frm.doc.loan_currency,
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


