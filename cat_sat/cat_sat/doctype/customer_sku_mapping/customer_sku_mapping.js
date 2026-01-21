// Copyright (c) 2026, IEA and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer SKU Mapping", {
    refresh(frm) {
        // Add button to show linked Cutting Specification
        if (frm.doc.item && !frm.is_new()) {
            frappe.db.get_value("Item", frm.doc.item, "cutting_specification", (r) => {
                if (r && r.cutting_specification) {
                    frm.add_custom_button(__("Xem Bảng cắt sắt"), () => {
                        frappe.set_route("Form", "Cutting Specification", r.cutting_specification);
                    });
                }
            });
        }
    }
});
