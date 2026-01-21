frappe.ui.form.on("Cutting Plan", {
	refresh(frm) {
		// Render progress dashboard
		render_progress_dashboard(frm);

		// Render time statistics
		render_time_statistics(frm);

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

				// Show dialog to input quantity
				const dialog = new frappe.ui.Dialog({
					title: `Nhập số lượng bộ: ${row.product_bundle}`,
					fields: [
						{
							fieldname: 'bundle_qty',
							fieldtype: 'Int',
							label: `Số lượng bộ (${bundle.description || ''})`,
							default: row.product_qty || 1,
							reqd: 1,
							description: `Bundle chứa: ${items.map(i => i.item_code).join(', ')}`
						}
					],
					primary_action_label: 'Thêm vào danh sách',
					primary_action(values) {
						const bundle_qty = values.bundle_qty || 1;

						// If only 1 item, set it directly
						if (items.length === 1) {
							frappe.model.set_value(cdt, cdn, "item_code", items[0].item_code);
							frappe.model.set_value(cdt, cdn, "product_qty", bundle_qty * items[0].qty);
							dialog.hide();
							frappe.show_alert({
								message: `Đã thêm ${bundle_qty} bộ`,
								indicator: "green"
							});
							return;
						}

						// Multiple items - expand into separate rows
						// Remove current row
						frm.get_field("items").grid.grid_rows_by_docname[cdn].remove();

						// Add individual items
						for (const item of items) {
							const new_row = frm.add_child("items");
							new_row.product_bundle = row.product_bundle;
							new_row.item_code = item.item_code;
							new_row.product_qty = bundle_qty * (item.qty || 1);
						}

						frm.refresh_field("items");
						dialog.hide();
						frappe.show_alert({
							message: `Đã thêm ${items.length} Items từ ${bundle_qty} bộ ${row.product_bundle}`,
							indicator: "green"
						});
					},
					secondary_action_label: 'Hủy',
					secondary_action() {
						// User canceled - clear product_bundle
						frappe.model.set_value(cdt, cdn, "product_bundle", "");
						dialog.hide();
					}
				});

				dialog.show();
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

function render_time_statistics(frm) {
	if (frm.is_new()) {
		frm.set_df_property('time_statistics', 'options', '<p class="text-muted">Lưu kế hoạch để xem thống kê thời gian</p>');
		return;
	}

	frm.call({
		method: 'get_progress_data',
		doc: frm.doc,
		callback(r) {
			if (!r.message || !r.message.time_statistics) {
				frm.set_df_property('time_statistics', 'options',
					'<p class="text-muted">Chưa có dữ liệu thời gian. Bắt đầu cắt để thu thập.</p>');
				return;
			}

			const stats = r.message.time_statistics;
			let html = '';

			// Summary card
			html += `
				<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin-bottom:15px;">
					<div style="background:#e3f2fd; padding:12px; border-radius:8px; text-align:center;">
						<div style="font-size:1.5em; font-weight:bold; color:#1976d2;">⏱️ ${stats.total_duration}</div>
						<div style="font-size:0.85em; color:#666;">Tổng thời gian cắt</div>
					</div>
					<div style="background:#e8f5e9; padding:12px; border-radius:8px; text-align:center;">
						<div style="font-size:1.5em; font-weight:bold; color:#388e3c;">📦 ${stats.total_qty_cut}</div>
						<div style="font-size:0.85em; color:#666;">Cây đã cắt</div>
					</div>
					<div style="background:#fff3e0; padding:12px; border-radius:8px; text-align:center;">
						<div style="font-size:1.5em; font-weight:bold; color:#f57c00;">📊 ${stats.avg_per_bar}</div>
						<div style="font-size:0.85em; color:#666;">TB / cây</div>
					</div>
					<div style="background:#fce4ec; padding:12px; border-radius:8px; text-align:center;">
						<div style="font-size:1.5em; font-weight:bold; color:#c2185b;">⏳ ${stats.estimated_remaining}</div>
						<div style="font-size:0.85em; color:#666;">Ước tính còn lại</div>
					</div>
				</div>
			`;

			// Target status
			if (stats.target_status) {
				const ts = stats.target_status;
				if (ts.status === 'ahead') {
					html += `<div style="background:#d4edda; padding:8px 15px; border-radius:5px; margin-bottom:15px;">
						<strong>🟢 Nhanh hơn kế hoạch ${ts.days} ngày</strong>
					</div>`;
				} else {
					html += `<div style="background:#f8d7da; padding:8px 15px; border-radius:5px; margin-bottom:15px;">
						<strong>🔴 Chậm hơn kế hoạch ${ts.days} ngày</strong>
					</div>`;
				}
			}

			// Timeline
			if (stats.first_start || stats.last_end) {
				html += `<div style="margin-bottom:15px; padding:10px; background:#f5f5f5; border-radius:5px;">
					<strong>Thời gian làm việc:</strong>
					${stats.first_start ? `Bắt đầu: <code>${stats.first_start}</code>` : ''}
					${stats.last_end ? ` → Cuối cùng: <code>${stats.last_end}</code>` : ''}
				</div>`;
			}

			// By Steel Profile table
			if (stats.by_profile && stats.by_profile.length > 0) {
				html += '<h6 style="margin-top:15px;">📊 Theo loại sắt</h6>';
				html += '<table class="table table-sm table-bordered" style="text-align:center">';
				html += '<thead style="background:#e3f2fd"><tr><th>Loại sắt</th><th>Số cây</th><th>Thời gian</th><th>TB/cây</th></tr></thead>';
				html += '<tbody>';
				for (const p of stats.by_profile) {
					html += `<tr>
						<td><strong>${p.profile}</strong></td>
						<td>${p.qty}</td>
						<td>${p.duration}</td>
						<td>${p.avg_per_bar}</td>
					</tr>`;
				}
				html += '</tbody></table>';
			}

			// By Machine table
			if (stats.by_machine && stats.by_machine.length > 0) {
				html += '<h6 style="margin-top:15px;">🔧 Hiệu suất máy</h6>';
				html += '<table class="table table-sm table-bordered" style="text-align:center">';
				html += '<thead style="background:#fff3e0"><tr><th>Máy</th><th>Số cây</th><th>Thời gian</th><th>TB/cây</th><th>Vấn đề</th></tr></thead>';
				html += '<tbody>';
				for (const m of stats.by_machine) {
					const issue_color = m.issues > 0 ? '#f8d7da' : '';
					html += `<tr style="background:${issue_color}">
						<td><strong>Máy ${m.machine}</strong></td>
						<td>${m.qty}</td>
						<td>${m.duration}</td>
						<td>${m.avg_per_bar}</td>
						<td>${m.issues > 0 ? `⚠️ ${m.issues}` : '✅'}</td>
					</tr>`;
				}
				html += '</tbody></table>';
			}

			// Issues list
			if (stats.issues && stats.issues.length > 0) {
				html += '<h6 style="margin-top:15px; color:#dc3545;">⚠️ Vấn đề ghi nhận</h6>';
				html += '<ul style="font-size:0.9em;">';
				for (const issue of stats.issues) {
					html += `<li><strong>Máy ${issue.machine}</strong>: ${issue.note} <span style="color:#888;">(${issue.pattern})</span></li>`;
				}
				html += '</ul>';
			}

			frm.set_df_property('time_statistics', 'options', html);
		}
	});
}
