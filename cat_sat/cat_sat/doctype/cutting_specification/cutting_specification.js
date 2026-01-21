/**
 * Cutting Specification - Client Script
 * 
 * Simplified design: Only details table (no separate pieces table)
 * piece_name and piece_qty are stored directly in each detail row
 */

frappe.ui.form.on('Cutting Specification', {
    refresh(frm) {
        // Add Import/Export buttons
        frm.add_custom_button(__('Tải Template Excel'), () => {
            window.open('/api/method/cat_sat.api.import_cutting_specification.download_template');
        }, __('Import/Export'));

        frm.add_custom_button(__('Import từ Excel'), () => {
            new frappe.ui.FileUploader({
                doctype: frm.doctype,
                docname: frm.docname,
                allow_multiple: false,
                restrictions: {
                    allowed_file_types: ['.xlsx', '.xls']
                },
                on_success: (file_doc) => {
                    frappe.call({
                        method: 'cat_sat.api.import_cutting_specification.import_from_excel',
                        args: {
                            file_url: file_doc.file_url
                        },
                        freeze: true,
                        freeze_message: 'Đang import...',
                        callback: (r) => {
                            if (r.message) {
                                frappe.msgprint({
                                    title: 'Import thành công',
                                    message: r.message.message,
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                }
            });
        }, __('Import/Export'));
    },

    // When item_template changes
    item_template(frm) {
        // BOM integration is optional - can load BOM items if needed
    }
});

// Trigger when adding/editing detail rows
frappe.ui.form.on('Cutting Detail', {
    details_add(frm, cdt, cdn) {
        // Set defaults for new row
        let row = frappe.get_doc(cdt, cdn);
        frappe.model.set_value(cdt, cdn, 'piece_qty', 1);
    }
});