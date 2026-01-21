"""
Script cập nhật Cutting Specification I3 với dữ liệu từ file Excel DinhMuc
Chạy với: bench --site erp.dongnama.app execute cat_sat.scripts.update_i3_cutting_spec.execute
"""
import frappe

def execute():
    # Parse Excel data for I3 cutting specification - 30 segments
    # bend_type chỉ chấp nhận: "Không", "Uốn 1 đầu", "Uốn 2 đầu", "Uốn cong"
    segments_data = [
        # I3.1.1 - Khung tựa (7 đoạn)
        {"segment_name": "I3.1.1.1", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "H10-20", "length_mm": 497, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong"},
        {"segment_name": "I3.1.1.2", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "H10-20", "length_mm": 355, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Uốn 1 đầu", "punch_hole_qty": 1},
        {"segment_name": "I3.1.1.3", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "FI19", "length_mm": 215, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không"},
        {"segment_name": "I3.1.1.4", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "V15", "length_mm": 425, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không", "rivet_hole_qty": 1},
        {"segment_name": "I3.1.1.5", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "V10", "length_mm": 425, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không"},
        {"segment_name": "I3.1.1.6", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "FI6", "length_mm": 40, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không"},
        {"segment_name": "I3.1.1.7", "piece_code": "I3.1", "piece_name": "Khung tựa", "steel_profile": "FI4", "length_mm": 60, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không"},
        
        # I3.1.2 - Tay trái (6 đoạn)
        {"segment_name": "I3.1.2.1", "piece_code": "I3.1", "piece_name": "Tay trái", "steel_profile": "FI19", "length_mm": 600, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong", "rivet_hole_qty": 1},
        {"segment_name": "I3.1.2.2", "piece_code": "I3.1", "piece_name": "Tay trái", "steel_profile": "FI19", "length_mm": 607, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn 1 đầu", "rivet_hole_qty": 1},
        {"segment_name": "I3.1.2.3", "piece_code": "I3.1", "piece_name": "Tay trái", "steel_profile": "V15", "length_mm": 420, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không", "rivet_hole_qty": 2},
        {"segment_name": "I3.1.2.4", "piece_code": "I3.1", "piece_name": "Tay trái", "steel_profile": "H10-20", "length_mm": 471, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong"},
        {"segment_name": "I3.1.2.5", "piece_code": "I3.1", "piece_name": "Tay trái", "steel_profile": "V10", "length_mm": 427, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong"},
        {"segment_name": "I3.1.2.6", "piece_code": "I3.1", "piece_name": "Tay trái", "steel_profile": "FI4", "length_mm": 60, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không"},
        
        # I3.1.3 - Tay phải (6 đoạn)
        {"segment_name": "I3.1.3.1", "piece_code": "I3.1", "piece_name": "Tay phải", "steel_profile": "FI19", "length_mm": 600, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong", "rivet_hole_qty": 1},
        {"segment_name": "I3.1.3.2", "piece_code": "I3.1", "piece_name": "Tay phải", "steel_profile": "FI19", "length_mm": 607, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn 1 đầu", "rivet_hole_qty": 1},
        {"segment_name": "I3.1.3.3", "piece_code": "I3.1", "piece_name": "Tay phải", "steel_profile": "V15", "length_mm": 420, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không", "rivet_hole_qty": 2},
        {"segment_name": "I3.1.3.4", "piece_code": "I3.1", "piece_name": "Tay phải", "steel_profile": "H10-20", "length_mm": 471, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong"},
        {"segment_name": "I3.1.3.5", "piece_code": "I3.1", "piece_name": "Tay phải", "steel_profile": "V10", "length_mm": 427, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong"},
        {"segment_name": "I3.1.3.6", "piece_code": "I3.1", "piece_name": "Tay phải", "steel_profile": "FI4", "length_mm": 60, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không"},
        
        # I3.1.4 - Mê ngồi (4 đoạn)
        {"segment_name": "I3.1.4.1", "piece_code": "I3.1", "piece_name": "Mê ngồi", "steel_profile": "V15", "length_mm": 445, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không", "punch_hole_qty": 1},
        {"segment_name": "I3.1.4.2", "piece_code": "I3.1", "piece_name": "Mê ngồi", "steel_profile": "V15", "length_mm": 400, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không", "punch_hole_qty": 2},
        {"segment_name": "I3.1.4.3", "piece_code": "I3.1", "piece_name": "Mê ngồi", "steel_profile": "V15", "length_mm": 175, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không", "punch_hole_qty": 1},
        {"segment_name": "I3.1.4.4", "piece_code": "I3.1", "piece_name": "Mê ngồi", "steel_profile": "V10", "length_mm": 422, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Uốn cong"},
        
        # I3.2.1 - Chân bàn (3 đoạn)
        {"segment_name": "I3.2.1.1", "piece_code": "I3.2", "piece_name": "Chân bàn", "steel_profile": "V15", "length_mm": 367, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không", "punch_hole_qty": 2},
        {"segment_name": "I3.2.1.2", "piece_code": "I3.2", "piece_name": "Chân bàn", "steel_profile": "V15", "length_mm": 420, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không", "rivet_hole_qty": 2},
        {"segment_name": "I3.2.1.3", "piece_code": "I3.2", "piece_name": "Chân bàn", "steel_profile": "V15", "length_mm": 367, "qty_per_unit": 1, "total_qty": 2, "bend_type": "Không"},
        
        # I3.2.2 - Hông bàn (2 đoạn)
        {"segment_name": "I3.2.2.1", "piece_code": "I3.2", "piece_name": "Hông bàn", "steel_profile": "V15", "length_mm": 324, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không"},
        {"segment_name": "I3.2.2.2", "piece_code": "I3.2", "piece_name": "Hông bàn", "steel_profile": "V15", "length_mm": 330, "qty_per_unit": 2, "total_qty": 4, "bend_type": "Không", "punch_hole_qty": 4},
        
        # I3.2.3 - Mặt bàn (2 đoạn)
        {"segment_name": "I3.2.3.1", "piece_code": "I3.2", "piece_name": "Mặt bàn", "steel_profile": "V15", "length_mm": 367, "qty_per_unit": 2, "total_qty": 2, "bend_type": "Không", "rivet_hole_qty": 2},
        {"segment_name": "I3.2.3.2", "piece_code": "I3.2", "piece_name": "Mặt bàn", "steel_profile": "V15", "length_mm": 397, "qty_per_unit": 2, "total_qty": 2, "bend_type": "Không"},
    ]

    # Get and update I3 Cutting Specification
    doc = frappe.get_doc("Cutting Specification", "I3")

    # Clear existing details
    doc.details = []

    # Add new details
    for idx, seg in enumerate(segments_data, 1):
        doc.append("details", {
            "idx": idx,
            "piece_name": seg.get("piece_name", ""),
            "piece_code": seg.get("piece_code", ""),
            "piece_qty": 1,
            "bom_item": f"MANH-{seg['piece_code']}",
            "steel_profile": seg.get("steel_profile", ""),
            "segment_name": seg.get("segment_name", ""),
            "length_mm": seg.get("length_mm", 0),
            "qty_per_unit": seg.get("qty_per_unit", 1),
            "total_qty": seg.get("total_qty", 1),
            "punch_hole_qty": seg.get("punch_hole_qty", 0),
            "rivet_hole_qty": seg.get("rivet_hole_qty", 0),
            "drill_hole_qty": seg.get("drill_hole_qty", 0),
            "bend_type": seg.get("bend_type", "Không"),
        })

    doc.save()
    frappe.db.commit()

    print(f"✅ Updated Cutting Specification I3 with {len(segments_data)} segments")
    print(f"   Pieces: {sorted(set([s['piece_name'] for s in segments_data]))}")
    print("   - Khung tựa: 7 đoạn")
    print("   - Tay trái: 6 đoạn")
    print("   - Tay phải: 6 đoạn")
    print("   - Mê ngồi: 4 đoạn")
    print("   - Chân bàn: 3 đoạn")
    print("   - Hông bàn: 2 đoạn")
    print("   - Mặt bàn: 2 đoạn")
