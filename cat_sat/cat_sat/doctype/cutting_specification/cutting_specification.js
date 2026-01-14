frappe.ui.form.on('Cutting Specification', {
    refresh(frm) {
        set_piece_select_options(frm);

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

    // Khi thêm/xóa mảnh ở bảng trên -> Cập nhật bảng dưới
    pieces_add(frm) {
        set_piece_select_options(frm);
    },
    pieces_remove(frm) {
        set_piece_select_options(frm);
    }
});

// Trigger khi sửa tên mảnh ở bảng trên
frappe.ui.form.on('Cutting Piece', {
    piece_name: function (frm) {
        set_piece_select_options(frm);
    }
});

// Trigger khi thêm dòng mới vào bảng chi tiết -> Cập nhật lại options ngay
frappe.ui.form.on('Cutting Detail', {
    details_add(frm) {
        set_piece_select_options(frm);
    }
});

function set_piece_select_options(frm) {
    let options = [];

    if (frm.doc.pieces && frm.doc.pieces.length > 0) {
        options = frm.doc.pieces
            .map(p => p.piece_name)
            .filter(Boolean);
        options = [...new Set(options)];
    }

    // Nếu không có mảnh nào, giữ giá trị mồi để Grid không bị lỗi
    let options_string = options.length > 0 ? options.join('\n') : "Chưa chọn";

    let grid = frm.fields_dict['details'].grid;

    // 1. Cập nhật metadata của cột
    grid.update_docfield_property('piece_name', 'options', options_string);

    // 2. [QUAN TRỌNG] Ép Grid vẽ lại dữ liệu để nhận diện dropdown mới
    // Lưu ý: Chỉ refresh nếu grid đã được render
    if (grid.wrapper) {
        grid.refresh();
    }
}