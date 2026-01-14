frappe.pages['cat-sat-mctd'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'MCTĐ Cutting Optimization',
        single_column: true
    });

    $(frappe.render_template('cat_sat_mctd')).appendTo(page.body);

    // Initialize
    cat_sat_mctd.init();
};

cat_sat_mctd = {
    hot: null,
    data: [
        ['', '', '', 1],
        ['', '', '', 1],
        ['', '', '', 1],
        ['', '', '', 1],
        ['', '', '', 1],
    ],

    init: function () {
        // Load steel profiles
        frappe.call({
            method: 'cat_sat.api.portal_api.get_steel_profiles',
            callback: function (r) {
                if (r.message) {
                    const select = document.getElementById('steel_profile');
                    r.message.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p.name;
                        opt.text = `${p.profile_code} - ${p.profile_name}`;
                        opt.setAttribute('data-factors', p.bundle_factors || '');
                        select.appendChild(opt);
                    });
                    cat_sat_mctd.update_factors();
                }
            }
        });

        // Init Handsontable
        if (typeof Handsontable !== 'undefined') {
            const container = document.getElementById('input_table');
            if (container) {
                this.hot = new Handsontable(container, {
                    data: this.data,
                    colHeaders: ['Tên đoạn', 'Dài (mm)', 'SL cần', 'Priority'],
                    columns: [
                        { type: 'text', width: 180 },
                        { type: 'numeric', width: 100 },
                        { type: 'numeric', width: 80 },
                        { type: 'numeric', width: 70 }
                    ],
                    minRows: 5,
                    rowHeaders: true,
                    contextMenu: true,
                    stretchH: 'all',
                    height: 280,
                    licenseKey: 'non-commercial-and-evaluation'
                });
            }
        }
    },

    update_factors: function () {
        const select = document.getElementById('steel_profile');
        if (select.selectedIndex >= 0) {
            const option = select.options[select.selectedIndex];
            document.getElementById('bundle_factors').value = option.getAttribute('data-factors') || '';
        }
    },

    add_row: function () {
        if (this.hot) {
            this.hot.alter('insert_row_below', this.hot.countRows() - 1);
        }
    },

    run_optimization: function () {
        if (!this.hot) {
            frappe.msgprint('Bảng nhập liệu chưa sẵn sàng');
            return;
        }

        const tableData = this.hot.getData();
        const items = [];

        for (const row of tableData) {
            if (row[1] && row[2]) {
                items.push({
                    segment_name: row[0] || '',
                    length_mm: parseFloat(row[1]),
                    qty: parseInt(row[2]),
                    priority: parseInt(row[3]) || 1
                });
            }
        }

        if (items.length === 0) {
            frappe.msgprint('Vui lòng nhập ít nhất 1 đoạn sắt!');
            return;
        }

        const payload = {
            steel_profile: document.getElementById('steel_profile').value,
            stock_length: parseFloat(document.getElementById('stock_length').value),
            trim_cut: 0,
            blade_width: parseFloat(document.getElementById('blade_width').value),
            manual_cut_limit: parseInt(document.getElementById('manual_cut_limit').value),
            max_surplus: parseInt(document.getElementById('max_surplus').value),
            items: items
        };

        document.getElementById('btn_optimize').disabled = true;
        document.getElementById('btn_optimize').innerHTML = '⏳ Đang tính...';

        frappe.call({
            method: 'cat_sat.api.portal_api.run_mctd_optimization',
            args: { data: JSON.stringify(payload) },
            callback: function (r) {
                document.getElementById('btn_optimize').disabled = false;
                document.getElementById('btn_optimize').innerHTML = '⚡ TỐI ƯU HÓA';

                if (r.message && r.message.success) {
                    document.getElementById('result_container').style.display = 'block';
                    document.getElementById('result_summary').innerHTML = r.message.result_html || '';
                    document.getElementById('result_container').scrollIntoView({ behavior: 'smooth' });
                } else {
                    frappe.msgprint('Lỗi: ' + (r.message?.error || 'Unknown error'));
                }
            },
            error: function (e) {
                document.getElementById('btn_optimize').disabled = false;
                document.getElementById('btn_optimize').innerHTML = '⚡ TỐI ƯU HÓA';
                frappe.msgprint('Lỗi kết nối: ' + e.message);
            }
        });
    }
};
