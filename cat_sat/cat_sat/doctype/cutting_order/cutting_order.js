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
        // Use frappe.ui.Dialog for better control over events and validation
        let d = new frappe.ui.Dialog({
            title: __("Xác nhận hoàn thành"),
            fields: [
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
                    options: ["", "1", "2", "3", "4"], // Add empty option to force selection if desired, or keep default
                    reqd: 1,
                    onchange: () => {
                        let machine = d.get_value("machine_no");
                        if (machine) {
                            let last_speed = localStorage.getItem(`catsat_laser_speed_machine_${machine}`);
                            if (last_speed) {
                                d.set_value("laser_speed", last_speed);
                            }
                        }
                    }
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
            ],
            primary_action_label: __("Lưu"),
            primary_action: (values) => {
                // Save laser speed for the selected machine
                if (values.machine_no && values.laser_speed) {
                    localStorage.setItem(`catsat_laser_speed_machine_${values.machine_no}`, values.laser_speed);
                    localStorage.setItem(`catsat_last_machine_no`, values.machine_no);
                }

                d.hide();
                catsat_execute_action(frm, row_idx, action, values.session_qty, values.machine_no, values.laser_speed, values.issue_note);
            }
        });

        // Load last used machine
        let last_machine = localStorage.getItem('catsat_last_machine_no');
        if (last_machine) {
            d.set_value('machine_no', last_machine);
            // Trigger speed load
            let last_speed = localStorage.getItem(`catsat_laser_speed_machine_${last_machine}`);
            if (last_speed) {
                d.set_value('laser_speed', last_speed);
            }
        }

        d.show();
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

                // Reload doc to get latest pattern statuses
                frm.reload_doc().then(() => {
                    // Also ensure items table is refreshed to show updated produced_qty and progress
                    if (action === "Stop") {
                        frm.refresh_field('items');
                    }
                });
            }
        }
    });
};

// Global handler for viewing pattern segment details
window.catsat_view_pattern_details = function (event, row_idx) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    let frm = cur_frm;
    if (!frm) return false;

    // Find the pattern row
    let pattern = frm.doc.optimization_result.find(r => r.idx === row_idx);
    if (!pattern) {
        frappe.msgprint(__("Không tìm thấy pattern"));
        return false;
    }

    // Fetch segments from database via custom whitelisted API
    frappe.call({
        method: "cat_sat.cat_sat.doctype.cutting_order.cutting_order.get_pattern_segments",
        args: {
            pattern_name: pattern.name
        },
        async: false,
        callback: function (r) {
            let segments = r.message || [];
            show_pattern_dialog(pattern, segments);
        }
    });

    return false;
};

// Helper function to show the pattern details dialog
function show_pattern_dialog(pattern, segments) {
    let table_html = `
        <div style="max-height: 400px; overflow-y: auto;">
        <table class="table table-bordered table-sm" style="font-size: 0.9em;">
            <thead style="position: sticky; top: 0; background: var(--card-bg);">
                <tr>
                    <th>Mã mảnh</th>
                    <th>Tên mảnh</th>
                    <th>Tên đoạn</th>
                    <th>Dài (mm)</th>
                    <th>SL</th>
                    <th>Lỗ dập</th>
                    <th>Lỗ tán</th>
                    <th>Lỗ khoan</th>
                    <th>Uốn</th>
                </tr>
            </thead>
            <tbody>`;

    if (segments.length === 0) {
        table_html += `<tr><td colspan="9" class="text-center text-muted">Chưa có chi tiết segment</td></tr>`;
    } else {
        segments.forEach(seg => {
            table_html += `
                <tr>
                    <td><code>${seg.piece_code || '-'}</code></td>
                    <td>${seg.piece_name || '-'}</td>
                    <td><strong>${seg.segment_name || '-'}</strong></td>
                    <td class="text-right">${seg.length_mm || 0}</td>
                    <td class="text-center"><strong>${seg.quantity || 0}</strong></td>
                    <td class="text-center">${seg.punch_holes || 0}</td>
                    <td class="text-center">${seg.rivet_holes || 0}</td>
                    <td class="text-center">${seg.drill_holes || 0}</td>
                    <td>${seg.bending || '-'}</td>
                </tr>`;
        });
    }

    table_html += `</tbody></table></div>`;

    // Show dialog
    let d = new frappe.ui.Dialog({
        title: `Chi tiết Pattern #${pattern.idx}: ${pattern.pattern}`,
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'info',
                options: `
                    <div class="row" style="margin-bottom: 10px;">
                        <div class="col-md-4"><strong>Sử dụng:</strong> ${pattern.used_length || 0} mm</div>
                        <div class="col-md-4"><strong>Hao hụt:</strong> ${pattern.waste || 0} mm</div>
                        <div class="col-md-4"><strong>Số cây:</strong> ${pattern.qty || 0}</div>
                    </div>
                `
            },
            {
                fieldtype: 'HTML',
                fieldname: 'segments_table',
                options: table_html
            }
        ]
    });
    d.show();
}

frappe.ui.form.on("Cutting Order", {
    setup(frm) {
        register_action_formatter();
    },

    onload(frm) {
        // Fetch default trim_cut from Cutting Settings on new document
        if (frm.is_new()) {
            frappe.db.get_single_value("Cutting Settings", "laser_trim_cut").then(value => {
                if (value && !frm.doc.trim_cut) {
                    frm.set_value("trim_cut", value);
                }
            });
        }
    },

    refresh(frm) {
        register_action_formatter();

        // Auto-sync bundle_factors from Steel Profile on refresh
        if (frm.doc.steel_profile) {
            frappe.db.get_value("Steel Profile", frm.doc.steel_profile, "bundle_factors", (r) => {
                if (r && r.bundle_factors) {
                    // Always update to match Steel Profile
                    frm.set_value("bundle_factors", r.bundle_factors);
                }
            });
        }

        // Add Run Optimization button
        if (!frm.is_new() && frm.doc.status !== "Completed" && frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Run Optimization"), () => {
                // Auto-save first, then run optimization
                frm.save().then(() => {
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
                });
            }).addClass("btn-primary");
        }

        // Force grid refresh and add row click handler
        if (frm.fields_dict.optimization_result && frm.fields_dict.optimization_result.grid) {
            let grid = frm.fields_dict.optimization_result.grid;

            setTimeout(() => {
                grid.refresh();

                // Add double-click handler to view pattern details
                $(grid.wrapper).off('dblclick', '.grid-row').on('dblclick', '.grid-row', function (e) {
                    // Don't trigger if clicking on buttons
                    if ($(e.target).closest('button').length) return;

                    let row_idx = $(this).data('idx');
                    if (row_idx) {
                        catsat_view_pattern_details(e, row_idx);
                    }
                });
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
    },

    steel_profile(frm) {
        // Auto-fetch bundle_factors from Steel Profile
        if (frm.doc.steel_profile) {
            frappe.db.get_value("Steel Profile", frm.doc.steel_profile, "bundle_factors", (r) => {
                if (r && r.bundle_factors) {
                    frm.set_value("bundle_factors", r.bundle_factors);
                } else {
                    frm.set_value("bundle_factors", "");
                }
            });
        } else {
            frm.set_value("bundle_factors", "");
        }
    },

    enable_bundling(frm) {
        // Switch trim_cut based on machine mode
        if (frm.doc.enable_bundling) {
            // MCTĐ mode - use mctd_trim_cut
            frappe.db.get_single_value("Cutting Settings", "mctd_trim_cut").then(value => {
                if (value) {
                    frm.set_value("trim_cut", value);
                }
            });
        } else {
            // Laser mode - use laser_trim_cut
            frappe.db.get_single_value("Cutting Settings", "laser_trim_cut").then(value => {
                if (value) {
                    frm.set_value("trim_cut", value);
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

        // View details button
        let view_onclick = `event.stopImmediatePropagation(); return window.catsat_view_pattern_details(event, ${doc.idx});`;

        return `<div style="display:flex; gap:3px;">
                    <button class="btn ${btn_class} btn-xs" 
                            onclick="${onclick}"
                            onmousedown="event.stopImmediatePropagation();"
                            ${btn_disabled}
                            style="flex:1; font-weight:bold; padding: 2px 6px;">
                        ${btn_text}
                    </button>
                    <button class="btn btn-info btn-xs" 
                            onclick="${view_onclick}"
                            onmousedown="event.stopImmediatePropagation();"
                            style="padding: 2px 6px;" title="Xem chi tiết">
                        👁
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
