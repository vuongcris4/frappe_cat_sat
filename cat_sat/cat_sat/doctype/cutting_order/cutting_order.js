// Copyright (c) 2026, IEA and contributors
// For license information, please see license.txt

// ============================================================
// CUTTING ORDER - Action Button Implementation
// Strategy: Use formatter with inline onclick handler
// ============================================================

// Global handler for START/STOP button clicks
window.catsat_handle_action = function (event, row_idx, current_status) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    let frm = cur_frm;
    if (!frm) {
        frappe.msgprint(__("Form not found"));
        return false;
    }

    console.log('[CatSat] Button clicked - row_idx:', row_idx, 'status:', current_status);

    let action = (current_status === "In Progress") ? "Stop" : "Start";

    if (action === "Stop") {
        frappe.prompt([
            {
                label: __("Số cây vừa cắt xong"),
                fieldname: "session_qty",
                fieldtype: "Int",
                reqd: 1,
                default: 1
            },
            {
                fieldtype: "Section Break",
                label: __("Thông tin máy (cho AI training)")
            },
            {
                label: __("Máy số"),
                fieldname: "machine_no",
                fieldtype: "Select",
                options: "\n1\n2\n3\n4"
            },
            {
                label: __("Tốc độ Laser (%)"),
                fieldname: "laser_speed",
                fieldtype: "Int"
            },
            {
                label: __("Ghi chú vấn đề"),
                fieldname: "issue_note",
                fieldtype: "Small Text"
            }
        ], (values) => {
            catsat_execute_action(frm, row_idx, action, values.session_qty, values.machine_no, values.laser_speed, values.issue_note);
        }, __("Xác nhận hoàn thành"), __("Lưu"));
    } else {
        catsat_execute_action(frm, row_idx, action, 0, null, null, null);
    }

    return false;
};

// Global handler for EDIT button clicks
window.catsat_edit_qty = function (event, row_idx, current_qty) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    let frm = cur_frm;
    if (!frm) {
        frappe.msgprint(__("Form not found"));
        return false;
    }

    frappe.prompt([
        {
            label: __("Số lượng mới"),
            fieldname: "new_qty",
            fieldtype: "Int",
            reqd: 1,
            default: current_qty || 0,
            description: __("Chỉ quản lý mới có quyền sửa số lượng")
        }
    ], (values) => {
        frappe.call({
            method: "cat_sat.cat_sat.doctype.cutting_order.cutting_order.update_cut_qty_wrapper",
            args: {
                order_name: frm.doc.name,
                row_idx: row_idx,
                new_qty: values.new_qty
            },
            freeze: true,
            freeze_message: __("Đang cập nhật..."),
            callback(r) {
                if (r.exc) {
                    console.error("[CatSat] Error:", r.exc);
                } else if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: __("Đã sửa số lượng từ {0} thành {1}", [r.message.old_qty, r.message.new_qty]),
                        indicator: 'green'
                    }, 5);
                    frm.reload_doc();
                }
            }
        });
    }, __("Sửa số lượng đã cắt"), __("Cập nhật"));

    return false;
};

// Execute START/STOP action via API
window.catsat_execute_action = function (frm, row_idx, action, qty, machine_no, laser_speed, issue_note) {
    frappe.call({
        method: "cat_sat.cat_sat.doctype.cutting_order.cutting_order.update_pattern_progress_wrapper",
        args: {
            order_name: frm.doc.name,
            row_idx: row_idx,
            action: action,
            session_qty: qty,
            machine_no: machine_no,
            laser_speed: laser_speed,
            issue_note: issue_note
        },
        freeze: true,
        freeze_message: (action === "Start") ? __("Đang bắt đầu...") : __("Đang lưu..."),
        callback(r) {
            if (r.exc) {
                console.error("[CatSat] Server Error:", r.exc);
                frappe.msgprint(__("Có lỗi xảy ra. Vui lòng thử lại."));
            } else {
                frappe.show_alert({
                    message: (action === "Start") ? __("Đã bắt đầu") : __("Đã dừng"),
                    indicator: 'green'
                }, 3);
                frm.reload_doc();
            }
        }
    });
};

frappe.ui.form.on("Cutting Order", {
    setup(frm) {
        register_action_formatter();
    },

    refresh(frm) {
        register_action_formatter();

        // Add Run Optimization button
        if (!frm.is_new() && frm.doc.status !== "Completed" && frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Run Optimization"), () => {
                frappe.call({
                    method: "cat_sat.services.cutting_optimization_service.run_optimization",
                    args: { order_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Running optimization algorithm..."),
                    callback(r) {
                        if (!r.exc) {
                            frm.reload_doc();
                            frappe.msgprint(__("Optimization completed successfully!"));
                        }
                    }
                });
            }).addClass("btn-primary");
        }

        // Force grid refresh
        if (frm.fields_dict.optimization_result && frm.fields_dict.optimization_result.grid) {
            setTimeout(() => {
                frm.fields_dict.optimization_result.grid.refresh();
            }, 100);
        }
    },

    stock_item(frm) {
        if (frm.doc.stock_item) {
            frappe.db.get_value("Item", frm.doc.stock_item, ["custom_length", "length"], (r) => {
                if (r && (r.custom_length || r.length)) {
                    frm.set_value("stock_length", r.custom_length || r.length);
                }
            });
        }
    }
});

// Register the formatter for action_btn field
function register_action_formatter() {
    if (!frappe.meta.docfield_map) return;
    if (!frappe.meta.docfield_map['Cutting Pattern']) return;
    if (!frappe.meta.docfield_map['Cutting Pattern']['action_btn']) return;

    frappe.meta.docfield_map['Cutting Pattern']['action_btn'].formatter = function (value, df, options, doc) {
        if (!doc || !doc.idx) return '';

        let status = doc.status || 'Pending';
        let cut_qty = doc.cut_qty || 0;
        let btn_class = 'btn-success';
        let btn_text = 'START';
        let btn_disabled = '';

        if (status === 'In Progress') {
            btn_class = 'btn-danger';
            btn_text = 'STOP';
        } else if (status === 'Completed') {
            btn_class = 'btn-secondary';
            btn_text = '✓ Xong';
            btn_disabled = 'disabled';
        }

        // Main action button
        let onclick = `event.stopImmediatePropagation(); return window.catsat_handle_action(event, ${doc.idx}, '${status}');`;

        // Edit button
        let edit_onclick = `event.stopImmediatePropagation(); return window.catsat_edit_qty(event, ${doc.idx}, ${cut_qty});`;

        return `<div style="display:flex; gap:3px;">
                    <button class="btn ${btn_class} btn-xs" 
                            onclick="${onclick}"
                            onmousedown="event.stopImmediatePropagation();"
                            ${btn_disabled}
                            style="flex:1; font-weight:bold; padding: 2px 6px;">
                        ${btn_text}
                    </button>
                    <button class="btn btn-default btn-xs" 
                            onclick="${edit_onclick}"
                            onmousedown="event.stopImmediatePropagation();"
                            style="padding: 2px 6px;" title="Sửa số lượng">
                        ✏️
                    </button>
                </div>`;
    };
}
