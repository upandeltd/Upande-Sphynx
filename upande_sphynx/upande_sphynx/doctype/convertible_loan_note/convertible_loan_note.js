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


