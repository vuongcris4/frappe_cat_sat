# apps/cat_sat/cat_sat/cat_sat/doctype/cutting_specification/cutting_specification.py
import frappe
from frappe.model.document import Document


class CuttingSpecification(Document):
	def validate(self):
		"""
		Hàm này chạy trước khi lưu dữ liệu vào database.
		Dùng validate() thay vì before_save() để đảm bảo dữ liệu sạch sẽ trước khi thực hiện bất kỳ tính toán nào.
		"""
		# 1. QUAN TRỌNG: Duyệt qua từng dòng Mảnh và xóa khoảng trắng thừa ngay lập tức
		if self.pieces:
			for row in self.pieces:
				if row.piece_name:
					# Cắt khoảng trắng 2 đầu và gán ngược lại
					row.piece_name = row.piece_name.strip()

		# 2. Tự động điền parent_spec_name (cho search)
		if self.spec_name:
			for piece in self.pieces:
				piece.parent_spec_name = self.spec_name

		# 3. Gọi hàm tính toán số lượng
		self.calculate_details_qty()

	def calculate_details_qty(self):
		"""Tính toán lại cột Total Qty trong bảng Chi tiết sắt"""
		# Tạo map: { "Tên mảnh đã sạch": Số lượng }
		piece_qty_map = {}
		if self.pieces:
			piece_qty_map = {p.piece_name: (p.piece_qty or 0) for p in self.pieces if p.piece_name}

		if self.details:
			for d in self.details:
				# Lấy tên mảnh ở bảng chi tiết
				raw_name = d.piece_name or ""

				# Cũng phải xóa khoảng trắng ở bảng chi tiết để khớp với bảng Mảnh
				clean_name = raw_name.strip()

				# Nếu tên mảnh trong detail có space thừa, tự sửa lại luôn cho đẹp
				if raw_name != clean_name:
					d.piece_name = clean_name

				if not clean_name:
					d.total_qty = 0
					continue

				# Lấy số lượng từ map
				piece_qty = piece_qty_map.get(clean_name, 0)

				# Tính toán
				d.total_qty = piece_qty * (d.qty_segment_per_piece or 0)

	def flatten_bom(self, product_qty: int):
		result = {}

		# Lấy map số lượng mảnh (đảm bảo sạch)
		piece_qty_map = {
			(p.piece_name.strip() if p.piece_name else ""): (p.piece_qty or 0) for p in self.pieces
		}

		for d in self.details:
			piece_name = d.piece_name
			if not piece_name:
				continue

			clean_name = piece_name.strip()
			piece_qty = piece_qty_map.get(clean_name, 0)

			# Tổng số đoạn cần cắt
			total_segment = (d.qty_segment_per_piece or 0) * piece_qty * product_qty

			# Key gom nhóm tối ưu
			key = (
				d.steel_profile,
				d.length_mm,
				d.bend_type,
				d.punch_hole_qty or 0,
				d.rivet_hole_qty or 0,
			)

			result[key] = result.get(key, 0) + total_segment

		return result
