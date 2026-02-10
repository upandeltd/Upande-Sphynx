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