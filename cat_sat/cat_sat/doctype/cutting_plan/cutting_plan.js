frappe.ui.form.on("Cutting Plan", {
	refresh(frm) {
		// Render progress dashboard
		render_progress_dashboard(frm);

		if (!frm.is_new() && frm.doc.status === "Draft") {
			frm.add_custom_button("Create Cutting Orders", () => {
				frappe.call({
					method: "cat_sat.services.cutting_plan_service.create_cutting_orders",
					args: {
						plan_name: frm.doc.name
					},
					freeze: true,
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
							frappe.msgprint("Đã tạo Lệnh cắt thành công. Vui lòng kiểm tra trên Dashboard.");
						}
					}
				});
			});
		}
	}
});

// Handle Product Bundle selection in Cutting Plan Item child table
frappe.ui.form.on("Cutting Plan Item", {
	product_bundle(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row.product_bundle) return;

		// Fetch Product Bundle items and expand
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Product Bundle",
				name: row.product_bundle
			},
			callback(r) {
				if (!r.message) return;

				const bundle = r.message;
				const items = bundle.items || [];

				if (items.length === 0) {
					frappe.msgprint("Product Bundle này không có Items");
					return;
				}

				// If only 1 item, set it directly
				if (items.length === 1) {
					frappe.model.set_value(cdt, cdn, "item_code", items[0].item_code);
					frappe.model.set_value(cdt, cdn, "product_qty", row.product_qty * items[0].qty);
					return;
				}

				// Multiple items - ask user to expand
				frappe.confirm(
					`Product Bundle "${row.product_bundle}" có ${items.length} Items. Bạn có muốn tách thành nhiều dòng?`,
					() => {
						// Remove current row and add individual items
						const current_qty = row.product_qty || 1;
						frm.get_field("items").grid.grid_rows_by_docname[cdn].remove();

						for (const item of items) {
							const new_row = frm.add_child("items");
							new_row.product_bundle = row.product_bundle;
							new_row.item_code = item.item_code;
							new_row.product_qty = current_qty * (item.qty || 1);
						}

						frm.refresh_field("items");
						frappe.show_alert({
							message: `Đã thêm ${items.length} Items từ Product Bundle`,
							indicator: "green"
						});
					},
					() => {
						// User canceled - clear product_bundle
						frappe.model.set_value(cdt, cdn, "product_bundle", "");
					}
				);
			}
		});
	}
});


function render_progress_dashboard(frm) {
	if (frm.is_new()) {
		frm.set_df_property('progress_summary', 'options', '<p class="text-muted">Lưu kế hoạch để xem tiến độ</p>');
		return;
	}

	frm.call({
		method: 'get_progress_data',
		doc: frm.doc,
		callback(r) {
			if (!r.message) {
				frm.set_df_property('progress_summary', 'options',
					'<p class="text-muted">Chưa có Cutting Order nào. Bấm "Create Cutting Orders" để tạo.</p>');
				return;
			}

			const data = r.message;
			let html = '';

			// Summary bar
			html += `
				<div style="margin-bottom:15px; padding:10px; background:#f5f5f5; border-radius:5px;">
					<div style="display:flex; justify-content:space-between; margin-bottom:10px;">
						<span><strong>Tổng tiến độ:</strong> ${data.summary.overall_percent}%</span>
						<span><strong>Số Cutting Order:</strong> ${data.summary.total_orders}</span>
					</div>
					<div style="background:#ddd; border-radius:3px; height:20px;">
						<div style="background:${data.summary.overall_percent >= 100 ? '#28a745' : '#007bff'}; 
							width:${Math.min(data.summary.overall_percent, 100)}%; 
							height:100%; border-radius:3px;"></div>
					</div>
				</div>
			`;

			// Complete products table (NEW)
			if (data.complete_products && data.complete_products.length > 0) {
				html += '<h5 style="margin-top:15px; color:#28a745;">🎉 Thành phẩm đủ bộ để xuất</h5>';
				html += '<table class="table table-sm table-bordered" style="text-align:center">';
				html += '<thead style="background:#d4edda"><tr><th>Item Code</th><th>Tên SP</th><th>Cần SX</th><th>Đủ bộ</th><th>Còn thiếu</th><th>%</th></tr></thead>';
				html += '<tbody>';
				for (const prod of data.complete_products) {
					const color = prod.percent >= 100 ? '#d4edda' : (prod.percent < 50 ? '#f8d7da' : '#fff3cd');
					html += `<tr style="background:${color};">
						<td><strong>${prod.item_code}</strong></td>
						<td>${prod.item_name || ''}</td>
						<td>${prod.qty_required}</td>
						<td><strong style="font-size:1.2em">${prod.qty_complete}</strong></td>
						<td>${prod.remaining}</td>
						<td>${prod.percent}%</td>
					</tr>`;

					// Detailed breakdown of pieces (if any)
					if (prod.pieces && prod.pieces.length > 0) {
						html += `<tr style="background:#f9f9f9;">
							<td colspan="6" style="text-align:left; padding:5px 20px;">
								<small><em>Chi tiết đồng bộ mảnh:</em></small>
								<div style="display:flex; flex-wrap:wrap; gap:10px; margin-top:5px;">`;

						for (const p of prod.pieces) {
							const p_color = p.allocated >= p.required ? '#28a745' : '#dc3545';
							html += `<span style="border:1px solid #ddd; padding:2px 6px; border-radius:3px; font-size:0.85em; background:#fff;">
								${p.piece_name}: <b style="color:${p_color}">${p.allocated}/${p.required}</b>
							</span>`;
						}

						html += `</div></td></tr>`;
					}
				}
				html += '</tbody></table>';
			}

			// Sync data - pieces ready for welding
			if (data.sync_data && data.sync_data.length > 0) {
				html += '<h5 style="margin-top:15px;">Đồng bộ hàn mảnh</h5>';
				for (const sync of data.sync_data) {
					html += `<div style="margin-bottom:10px; border-left:3px solid #6c757d; padding-left:10px;">`;
					html += `<strong>${sync.spec_name}</strong>`;
					html += `<table class="table table-sm table-bordered" style="margin-top:5px;">
						<thead><tr>
							<th>Mảnh</th>
							<th>Cần</th>
							<th>Đủ bộ</th>
							<th>Thiếu</th>
						</tr></thead><tbody>`;
					for (const piece of sync.pieces) {
						const color = piece.percent >= 100 ? '#d4edda' : (piece.percent < 50 ? '#f8d7da' : '');
						html += `<tr style="background:${color};">
							<td>${piece.piece_name}</td>
							<td>${piece.qty_required}</td>
							<td><strong>${piece.complete_pieces}</strong></td>
							<td>${piece.remaining}</td>
						</tr>`;
					}
					html += `</tbody></table></div>`;
				}
			}

			// Segment progress table
			if (data.segments && data.segments.length > 0) {
				html += `
					<h5 style="margin-top:15px;">Chi tiết đoạn sắt</h5>
					<table class="table table-sm table-bordered">
						<thead><tr>
							<th>Loại sắt</th>
							<th>Tên đoạn</th>
							<th>Dài (mm)</th>
							<th>Cần</th>
							<th>Đã cắt</th>
							<th>Còn</th>
							<th>%</th>
						</tr></thead><tbody>
				`;
				for (const seg of data.segments) {
					const color = seg.percent >= 100 ? '#d4edda' : (seg.percent < 50 ? '#f8d7da' : '');
					html += `<tr style="background:${color};">
						<td>${seg.steel_profile || ''}</td>
						<td>${seg.segment_name}</td>
						<td>${seg.length_mm}</td>
						<td>${seg.required}</td>
						<td>${seg.produced}</td>
						<td>${seg.remaining}</td>
						<td>${seg.percent}%</td>
					</tr>`;
				}
				html += '</tbody></table>';
			}

			frm.set_df_property('progress_summary', 'options', html);
		}
	});
}
