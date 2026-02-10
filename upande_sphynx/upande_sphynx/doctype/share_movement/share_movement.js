// Copyright (c) 2025, Jeniffer and contributors
// For license information, please see license.txt

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

