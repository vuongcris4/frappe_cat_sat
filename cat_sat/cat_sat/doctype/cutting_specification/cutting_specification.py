# apps/cat_sat/cat_sat/cat_sat/doctype/cutting_specification/cutting_specification.py
"""
Cutting Specification - Định mức cắt sắt cho sản phẩm

Cấu trúc theo thiết kế IEA:
- item_template: Link đến Item (sản phẩm)
- customer: Link đến Customer (nếu spec riêng khách)
- pieces: Table các mảnh hàn (piece_code, piece_name, piece_qty)
- details: Table chi tiết đoạn sắt (piece_name, steel_profile, length_mm, qty_per_unit)
"""
import frappe
from frappe.model.document import Document


class CuttingSpecification(Document):
    def validate(self):
        """Validate before save"""
        # 1. Validate piece names in details against pieces table
        self.validate_piece_names()
        
        # 2. Update piece_code from selected piece_name
        self.update_piece_codes()
        
        # 3. Calculate total quantities
        self.calculate_details_qty()

    def get_pieces_map(self):
        """Build map of piece_name -> {piece_code, piece_qty} from pieces table"""
        pieces_map = {}
        if hasattr(self, 'pieces') and self.pieces:
            for p in self.pieces:
                # Key by "piece_code - piece_name" format used in Select
                key = f"{p.piece_code} - {p.piece_name}" if p.piece_code else p.piece_name
                pieces_map[key] = {
                    "piece_code": p.piece_code,
                    "piece_name": p.piece_name,
                    "piece_qty": p.piece_qty or 1
                }
                # Also allow lookup by piece_name only
                pieces_map[p.piece_name] = pieces_map[key]
        return pieces_map

    def get_piece_qty_map(self):
        """Build map of piece_name -> qty from pieces table"""
        if not hasattr(self, 'pieces') or not self.pieces:
            return {}
        return {p.piece_name: p.piece_qty or 1 for p in self.pieces}

    def validate_piece_names(self):
        """Check if piece_name in details exists in pieces table"""
        if not hasattr(self, 'pieces') or not self.pieces or not self.details:
            return
        
        valid_names = set()
        for p in self.pieces:
            valid_names.add(p.piece_name)
            if p.piece_code:
                valid_names.add(f"{p.piece_code} - {p.piece_name}")
        
        orphan_pieces = set()
        for detail in self.details:
            if detail.piece_name and detail.piece_name not in valid_names:
                orphan_pieces.add(detail.piece_name)
        
        if orphan_pieces:
            frappe.msgprint(
                f"⚠️ Các mảnh sau không có trong danh sách: {', '.join(orphan_pieces)}",
                indicator="orange",
                title="Cảnh báo: Mảnh không tồn tại"
            )

    def update_piece_codes(self):
        """Update piece_code in details from pieces table"""
        if not self.details or not hasattr(self, 'pieces') or not self.pieces:
            return
        
        pieces_map = self.get_pieces_map()
        
        for d in self.details:
            if d.piece_name and d.piece_name in pieces_map:
                d.piece_code = pieces_map[d.piece_name].get("piece_code", "")

    def calculate_details_qty(self):
        """Calculate total_qty for each detail row
        
        Since the new schema uses bom_item (links to PHOI items) instead of pieces table,
        we simply calculate: total_qty = qty_per_unit (the pieces logic is deprecated)
        """
        if self.details:
            for d in self.details:
                # Simple calculation - qty_per_unit IS the total for 1 product
                # The pieces table multiplier is no longer used
                d.total_qty = d.qty_per_unit or 0

    def flatten_bom(self, product_qty: int):
        """Flatten cutting spec for optimization
        
        Returns dict of {(steel_profile, length, bend_type, holes...): total_qty}
        """
        result = {}

        for d in self.details:
            if not d.bom_item:
                continue

            # Total segments = qty_per_unit * product_qty
            # (bom_item already represents a piece, no multiplier needed)
            total_segment = (d.qty_per_unit or 0) * product_qty

            # Key for grouping optimization
            key = (
                d.steel_profile,
                d.length_mm,
                d.bend_type or "Không",
                d.punch_hole_qty or 0,
                d.rivet_hole_qty or 0,
            )

            result[key] = result.get(key, 0) + total_segment

        return result

    def get_material_summary(self, bom_item=None):
        """
        Calculate total steel length needed per profile.
        Returns: {steel_profile: total_length_mm}
        """
        summary = {}
        
        for d in self.details:
            # Filter by bom_item if specified
            if bom_item and d.bom_item != bom_item:
                continue
            
            steel = d.steel_profile
            # Length = length_mm * qty_per_unit (one product)
            length = d.length_mm * (d.qty_per_unit or 0)
            
            summary[steel] = summary.get(steel, 0) + length
        
        return summary


@frappe.whitelist()
def get_pieces_for_spec(spec_name):
    """API to get pieces list for frontend dropdown"""
    if not spec_name:
        return []
    
    pieces = frappe.get_all("Cutting Piece",
        filters={"parent": spec_name, "parenttype": "Cutting Specification"},
        fields=["piece_code", "piece_name", "piece_qty"],
        order_by="idx"
    )
    
    # Format for Select options: "piece_code - piece_name"
    options = []
    for p in pieces:
        if p.piece_code:
            options.append(f"{p.piece_code} - {p.piece_name}")
        else:
            options.append(p.piece_name)
    
    return options


@frappe.whitelist()
def get_bom_items_for_item(item_code):
    """API to get BOM items for item (legacy compatibility)"""
    if not item_code:
        return []
    
    bom_name = frappe.db.get_value("BOM", {
        "item": item_code,
        "is_active": 1,
        "is_default": 1
    }, "name")
    
    if not bom_name:
        return []
    
    items = frappe.get_all("BOM Item",
        filters={"parent": bom_name},
        fields=["item_code", "item_name", "qty"],
        order_by="idx"
    )
    
    return items
