frappe.pages['cat-sat-portal'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Portal Cắt Sắt',
        single_column: true
    });

    $(frappe.render_template('cat_sat_portal')).appendTo(page.body);
};
