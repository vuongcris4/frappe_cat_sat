// Cat Sat: Production Plan Custom Script
// Adds button to generate Cutting Plans from Production Plan

frappe.ui.form.on('Production Plan', {
    refresh: function (frm) {
        // Add button only for submitted Production Plans
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Tạo KH Cắt Sắt'), function () {
                frappe.call({
                    method: 'cat_sat.api.production_plan.generate_cutting_plans',
                    args: {
                        production_plan: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Đang tạo kế hoạch cắt sắt...'),
                    callback: function (r) {
                        if (r.message && r.message.length > 0) {
                            frm.reload_doc();

                            // Show link to created Cutting Plans
                            let links = r.message.map(cp =>
                                `<a href="/app/cutting-plan/${cp}">${cp}</a>`
                            ).join(', ');

                            frappe.msgprint({
                                title: __('Thành công'),
                                indicator: 'green',
                                message: __('Đã tạo {0} Kế hoạch cắt: {1}', [r.message.length, links])
                            });
                        }
                    }
                });
            }, __('Cat Sat'));

            // Add button to view existing Cutting Plans
            frappe.call({
                method: 'cat_sat.api.production_plan.get_cutting_plans_for_production_plan',
                args: {
                    production_plan: frm.doc.name
                },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        frm.add_custom_button(__('Xem KH Cắt Sắt ({0})', [r.message.length]), function () {
                            frappe.set_route('List', 'Cutting Plan', {
                                work_order: frm.doc.name
                            });
                        }, __('Cat Sat'));
                    }
                }
            });
        }

        // For draft plans, show a different message
        if (frm.doc.docstatus === 0) {
            frm.dashboard.add_comment(
                __('Submit Production Plan để tạo Kế hoạch cắt sắt'),
                'blue',
                true
            );
        }
    }
});
