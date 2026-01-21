frappe.ui.form.on('Item', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            frappe.call({
                method: "cat_sat.api.item_info.get_customer_skus",
                args: { item_code: frm.doc.item_code },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        render_customer_skus(frm, r.message);
                    }
                }
            });
        }
    }
});

function render_customer_skus(frm, skus) {
    let html = `
        <table class="table table-bordered table-condensed table-hover" style="margin-bottom: 0;">
            <thead>
                <tr class="active">
                    <th style="width: 25%">Khách hàng</th>
                    <th style="width: 25%">SKU Khách</th>
                    <th style="width: 20%">Barcode</th>
                    <th>Mô tả</th>
                </tr>
            </thead>
            <tbody>
                ${skus.map(s => `
                    <tr>
                        <td style="font-weight: 500;">${s.customer}</td>
                        <td style="font-weight: bold; color: var(--primary);">
                            <a href="/app/customer-sku-mapping/${s.customer_sku}">
                                ${s.customer_sku}
                            </a>
                        </td>
                        <td>${s.barcode || ''}</td>
                        <td class="text-muted small">${s.description || ''}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    // Remove existing section if any to avoid duplicates
    if (frm.dashboard.wrapper) {
        frm.dashboard.wrapper.find('.customer-sku-section').remove();

        // Create a new section
        let $section = $(`
            <div class="form-dashboard-section customer-sku-section" style="margin-bottom: 15px;">
                <div class="section-head" style="margin-bottom: 10px; font-weight: bold; text-transform: uppercase; color: #737373; font-size: 11px; letter-spacing: 0.4px;">
                    Mã SKU Khách Hàng (Customer Mapping)
                </div>
                <div class="section-body" style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 4px; overflow: hidden;">
                    ${html}
                </div>
            </div>
        `);

        // Prepend to dashboard
        frm.dashboard.wrapper.prepend($section);
        $section.show();
    }
}
