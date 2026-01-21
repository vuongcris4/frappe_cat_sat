"""
Demo Data Script - SKU to Cutting Specification Flow
Tạo dữ liệu mẫu:
- Item Attributes: Wire Color (Màu Dây), Cushion Color (Màu Nệm), Table Surface (Mặt Bàn)
- Items: J55.T4, J55.C (Templates với variants)
- Customer SKU Mapping: SKU → Variant Item (e.g., J55.C-DAY.DEN-NEM.BE)
- Product Bundle: SET-J55-T4-LONGTECH (chỉ dùng khi gộp bộ)

Variant Naming Convention:
- Template: J55.C, J55.T4
- Variant: J55.C-DAY.<abbr>-NEM.<abbr> hoặc J55.T4-DAY.<abbr>-MAT.<abbr>
- Prefixes: DAY=Dây, NEM=Nệm, MAT=Mặt bàn
"""
import frappe
from frappe.utils import nowdate


# ================== DATA DEFINITIONS ==================

WIRE_COLORS = [
    {"value": "Bán nguyệt", "abbr": "BNG"},
    {"value": "Đen", "abbr": "DEN"},
    {"value": "Nâu", "abbr": "NAU"},
    {"value": "Xám be", "abbr": "XBE"},
    {"value": "Xám bông", "abbr": "XBO"},
    {"value": "Đen nâu", "abbr": "DNA"},
    {"value": "Nâu đốm", "abbr": "NDO"},
    {"value": "Dây cạp đôi", "abbr": "DCD"},
    {"value": "Vàng 29", "abbr": "V29"},
    {"value": "Nâu 08", "abbr": "N08"},
    {"value": "Nâu 3 khía", "abbr": "N3K"},
    {"value": "Nâu 04", "abbr": "N04"},
    {"value": "Nâu chữ h", "abbr": "NCH"},
    {"value": "Sht21", "abbr": "S21"},
]

CUSHION_COLORS = [
    {"value": "Be", "abbr": "BE"},
    {"value": "Đỏ", "abbr": "DO"},
]

TABLE_SURFACES = [
    {"value": "Kính", "abbr": "KINH"},
    {"value": "Gỗ", "abbr": "GO"},
]

# Customer codes for customer-specific items
CUSTOMERS = [
    {"name": "Meying", "abbr": "MY"},
    {"name": "Goplus", "abbr": "GP"},
    {"name": "Vidaxl", "abbr": "VX"},
    {"name": "NUU", "abbr": "NU"},
]


@frappe.whitelist()
def create_j55_demo():
    """Tạo full demo data cho dòng sản phẩm J55 với Item Variants"""
    results = []
    
    frappe.db.begin()
    try:
        # 0. Tạo Item Attributes (Wire Color, Cushion Color, Table Surface)
        create_item_attributes()
        results.append("✅ Item Attributes (Wire/Cushion/Surface)")
        
        # 1. Tạo Steel Profiles nếu chưa có
        create_steel_profiles()
        results.append("✅ Steel Profiles")
        
        # 2. Tạo Template Items: J55.T4, J55.C (has_variants=1)
        create_j55_template_items()
        results.append("✅ Template Items: J55.T4, J55.C")
        
        # 3. Tạo Cutting Specifications (link với Template)
        create_j55_cutting_specs()
        results.append("✅ Cutting Specifications")
        
        # 4. Tạo Variant Items
        create_j55_variants()
        results.append("✅ Variant Items (J55.C-DAY.xxx-NEM.xxx, ...)")
        
        # 5. Tạo Customer SKU Mappings (link đến Variants)
        create_customer_sku_mappings()
        results.append("✅ Customer SKU Mappings → Variants")
        
        frappe.db.commit()
        return {"status": "success", "results": results}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Demo data error: {e}", "J55 Demo")
        return {"status": "error", "message": str(e)}


def create_steel_profiles():
    """Tạo Steel Profiles từ định mức"""
    profiles = [
        {"profile_code": "V12", "shape": "V", "dimension": "12", "bundle_factors": "35 40 45"},
        {"profile_code": "V15", "shape": "V", "dimension": "15", "bundle_factors": "27 30 33 36 39"},
        {"profile_code": "V20", "shape": "V", "dimension": "20", "bundle_factors": "20 25 30"},
        {"profile_code": "V50", "shape": "V", "dimension": "50", "bundle_factors": "10 12 14"},
        {"profile_code": "H10-20", "shape": "H", "dimension": "10x20", "bundle_factors": "25 30 35"},
        {"profile_code": "H25-50", "shape": "H", "dimension": "25x50", "bundle_factors": "15 18 20"},
        {"profile_code": "Fi4", "shape": "FI", "dimension": "4", "bundle_factors": "50 60 70"},
        {"profile_code": "Fi6", "shape": "FI", "dimension": "6", "bundle_factors": "40 50 60"},
        {"profile_code": "Fi16", "shape": "FI", "dimension": "16", "bundle_factors": "20 25 30"},
        {"profile_code": "Fi21", "shape": "FI", "dimension": "21", "bundle_factors": "15 20 25"},
    ]
    
    for p in profiles:
        if not frappe.db.exists("Steel Profile", p["profile_code"]):
            doc = frappe.new_doc("Steel Profile")
            doc.profile_code = p["profile_code"]
            doc.shape = p["shape"]
            doc.dimension = p["dimension"]
            doc.bundle_factors = p.get("bundle_factors", "")
            doc.insert(ignore_permissions=True)


def create_j55_items():
    """DEPRECATED - Use create_j55_template_items() instead"""
    create_j55_template_items()


def create_item_attributes():
    """Tạo Item Attributes: Wire Color, Cushion Color, Table Surface, Customer Code"""
    
    attributes = [
        {"name": "Wire Color", "label": "Màu Dây", "values": WIRE_COLORS},
        {"name": "Cushion Color", "label": "Màu Nệm", "values": CUSHION_COLORS},
        {"name": "Table Surface", "label": "Mặt Bàn", "values": TABLE_SURFACES},
        {"name": "Customer Code", "label": "Mã Khách Hàng", "values": [
            {"value": c["abbr"], "abbr": c["abbr"]} for c in CUSTOMERS
        ]},
    ]
    
    for attr in attributes:
        attr_name = attr["name"]
        if not frappe.db.exists("Item Attribute", attr_name):
            doc = frappe.get_doc({
                "doctype": "Item Attribute",
                "attribute_name": attr_name,
                "numeric_values": 0
            })
            doc.insert(ignore_permissions=True)
        
        # Add attribute values
        doc = frappe.get_doc("Item Attribute", attr_name)
        existing_values = {v.attribute_value for v in doc.item_attribute_values}
        
        for value in attr["values"]:
            if value["value"] not in existing_values:
                doc.append("item_attribute_values", {
                    "attribute_value": value["value"],
                    "abbr": value["abbr"]
                })
        
        doc.save(ignore_permissions=True)


def create_j55_template_items():
    """Tạo Template Items cho dòng J55 với has_variants=1"""
    
    # Tạo Item Group nếu chưa có
    if not frappe.db.exists("Item Group", "Sản phẩm IEA"):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "Sản phẩm IEA",
            "parent_item_group": "All Item Groups"
        }).insert(ignore_permissions=True)
    
    # Lưu ý: Customer Code là optional, để đầu tiên để dễ nhìn
    templates = [
        {
            "item_code": "J55.T4",
            "item_name": "Bàn JSE 55 - 4 ghế",
            "factory_code": "J55",
            "item_group": "Sản phẩm IEA",
            "stock_uom": "Cái",
            "has_variants": 1,
            "attributes": ["Customer Code", "Wire Color", "Table Surface"],
        },
        {
            "item_code": "J55.T6", 
            "item_name": "Bàn JSE 55 - 6 ghế",
            "factory_code": "J55",
            "item_group": "Sản phẩm IEA",
            "stock_uom": "Cái",
            "has_variants": 1,
            "attributes": ["Customer Code", "Wire Color", "Table Surface"],
        },
        {
            "item_code": "J55.C",
            "item_name": "Ghế JSE 55",
            "factory_code": "J55",
            "item_group": "Sản phẩm IEA",
            "stock_uom": "Cái",
            "has_variants": 1,
            "attributes": ["Customer Code", "Wire Color", "Cushion Color"],
        },
    ]
    
    for tpl in templates:
        if not frappe.db.exists("Item", tpl["item_code"]):
            doc = frappe.new_doc("Item")
            doc.item_code = tpl["item_code"]
            doc.item_name = tpl["item_name"]
            doc.item_group = tpl["item_group"]
            doc.stock_uom = tpl["stock_uom"]
            doc.is_stock_item = 0  # Template không track stock
            doc.has_variants = 1
            doc.factory_code = tpl.get("factory_code", "")
            
            for attr in tpl["attributes"]:
                doc.append("attributes", {"attribute": attr})
            
            doc.insert(ignore_permissions=True)
        else:
            # Update existing item to be template if needed
            doc = frappe.get_doc("Item", tpl["item_code"])
            if not doc.has_variants:
                doc.has_variants = 1
                doc.is_stock_item = 0
                for attr in tpl["attributes"]:
                    if not any(a.attribute == attr for a in doc.attributes):
                        doc.append("attributes", {"attribute": attr})
                doc.save(ignore_permissions=True)


def create_j55_cutting_specs():
    """Tạo Cutting Specifications cho J55 - Ghế và Bàn từ BOM thực tế"""
    
    # === Spec cho Ghế J55.C (Screenshot 1: 55.1 - 55.5) ===
    if not frappe.db.exists("Cutting Specification", {"spec_name": "Ghế JSE 55"}):
        spec = frappe.new_doc("Cutting Specification")
        spec.spec_name = "Ghế JSE 55"
        
        # 55.1 - Khung tựa (pieces)
        spec.append("pieces", {"piece_code": "55.1", "piece_name": "Khung tựa", "piece_qty": 1})
        
        # 55.1 Details
        details_55_1 = [
            {"segment": "55.1.1", "steel": "Fi21", "length": 499, "qty": 1, "bend": "Uốn"},
            {"segment": "55.1.2", "steel": "Fi21", "length": 254, "qty": 2, "bend": ""},
            {"segment": "55.1.3", "steel": "H10-20", "length": 47, "qty": 2, "bend": "Uốn, 1 đập"},
            {"segment": "55.1.4", "steel": "V20", "length": 40.5, "qty": 1, "bend": "1 tán"},
            {"segment": "55.1.6", "steel": "V12", "length": 40.5, "qty": 1, "bend": "Uốn"},
            {"segment": "55.1.7", "steel": "Fi4", "length": 6, "qty": 2, "bend": ""},
            {"segment": "55.1.8", "steel": "Fi6", "length": 4, "qty": 2, "bend": ""},
        ]
        for d in details_55_1:
            spec.append("details", {
                "piece_name": "55.1 - Khung tựa",
                "steel_profile": d["steel"],
                "segment_name": d["segment"],
                "length_mm": d["length"],
                "qty_segment_per_piece": d["qty"],
                "bend_type": d.get("bend", "")
            })
        
        # 55.2 - Tay trái
        spec.append("pieces", {"piece_code": "55.2", "piece_name": "Tay trái", "piece_qty": 1})
        details_55_2 = [
            {"segment": "55.2.1", "steel": "Fi21", "length": 60, "qty": 1, "bend": "Uốn, 1 tán"},
            {"segment": "55.2.2", "steel": "Fi21", "length": 60, "qty": 1, "bend": "1 tán"},
            {"segment": "55.2.3", "steel": "Fi16", "length": 5, "qty": 1, "bend": ""},
            {"segment": "55.2.4", "steel": "V12", "length": 51, "qty": 1, "bend": "Uốn"},
            {"segment": "55.2.5", "steel": "V12", "length": 50, "qty": 1, "bend": "Uốn"},
            {"segment": "55.2.7", "steel": "V12", "length": 44, "qty": 1, "bend": "Uốn"},
            {"segment": "55.2.8", "steel": "H10-20", "length": 45, "qty": 1, "bend": "2 tán"},
            {"segment": "55.2.9", "steel": "Fi4", "length": 19, "qty": 1, "bend": ""},
            {"segment": "55.2.10", "steel": "H10-20", "length": 2, "qty": 1, "bend": ""},
            {"segment": "55.2.11", "steel": "Fi4", "length": 6, "qty": 2, "bend": ""},
        ]
        for d in details_55_2:
            spec.append("details", {
                "piece_name": "55.2 - Tay trái",
                "steel_profile": d["steel"],
                "segment_name": d["segment"],
                "length_mm": d["length"],
                "qty_segment_per_piece": d["qty"],
                "bend_type": d.get("bend", "")
            })
        
        # 55.3 - Tay phải (same as tay trái)
        spec.append("pieces", {"piece_code": "55.3", "piece_name": "Tay phải", "piece_qty": 1})
        for d in details_55_2:  # Same details as tay trái
            spec.append("details", {
                "piece_name": "55.3 - Tay phải",
                "steel_profile": d["steel"],
                "segment_name": d["segment"].replace("55.2", "55.3"),
                "length_mm": d["length"],
                "qty_segment_per_piece": d["qty"],
                "bend_type": d.get("bend", "")
            })
        
        # 55.4 - Mê ngồi
        spec.append("pieces", {"piece_code": "55.4", "piece_name": "Mê ngồi", "piece_qty": 1})
        details_55_4 = [
            {"segment": "55.4.1", "steel": "V20", "length": 46, "qty": 1, "bend": "2 tán"},
            {"segment": "55.4.2", "steel": "H10-20", "length": 43, "qty": 2, "bend": "2 đập"},
            {"segment": "55.4.3", "steel": "H10-20", "length": 42.5, "qty": 1, "bend": "1 đập"},
            {"segment": "55.4.4", "steel": "Fi6", "length": 6, "qty": 4, "bend": ""},
        ]
        for d in details_55_4:
            spec.append("details", {
                "piece_name": "55.4 - Mê ngồi",
                "steel_profile": d["steel"],
                "segment_name": d["segment"],
                "length_mm": d["length"],
                "qty_segment_per_piece": d["qty"],
                "bend_type": d.get("bend", "")
            })
        
        # 55.5 - Hông trước
        spec.append("pieces", {"piece_code": "55.5", "piece_name": "Hông trước", "piece_qty": 1})
        details_55_5 = [
            {"segment": "55.5.1", "steel": "H10-20", "length": 46, "qty": 1, "bend": "2 đập"},
            {"segment": "55.5.2", "steel": "H10-20", "length": 19, "qty": 2, "bend": "1 đập"},
            {"segment": "55.5.4", "steel": "V12", "length": 44, "qty": 1, "bend": "Uốn"},
            {"segment": "55.5.5", "steel": "Fi4", "length": 6, "qty": 2, "bend": ""},
        ]
        for d in details_55_5:
            spec.append("details", {
                "piece_name": "55.5 - Hông trước",
                "steel_profile": d["steel"],
                "segment_name": d["segment"],
                "length_mm": d["length"],
                "qty_segment_per_piece": d["qty"],
                "bend_type": d.get("bend", "")
            })
        
        spec.insert(ignore_permissions=True)
        frappe.db.set_value("Item", "J55.C", "cutting_specification", spec.name)
    
    # === Spec cho Bàn J55.T4 (Screenshot 2: Bàn 4) ===
    if not frappe.db.exists("Cutting Specification", {"spec_name": "Bàn JSE 55 - 4 ghế"}):
        spec = frappe.new_doc("Cutting Specification")
        spec.spec_name = "Bàn JSE 55 - 4 ghế"
        
        # 55.4.1 - Viền ngắn
        spec.append("pieces", {"piece_code": "55.4.1", "piece_name": "Viền ngắn", "piece_qty": 1})
        spec.append("details", {
            "piece_name": "55.4.1 - Viền ngắn",
            "steel_profile": "H25-50",
            "segment_name": "55.4.1.1",
            "length_mm": 695,
            "qty_segment_per_piece": 4,
        })
        spec.append("details", {
            "piece_name": "55.4.1 - Viền ngắn",
            "steel_profile": "H25-50",
            "segment_name": "55.4.1.1 - Pát hộp",
            "length_mm": 90,
            "qty_segment_per_piece": 8,
            "punch_hole_qty": 2
        })
        
        # 55.4.2 - Chân bàn
        spec.append("pieces", {"piece_code": "55.4.2", "piece_name": "Chân bàn", "piece_qty": 1})
        spec.append("details", {
            "piece_name": "55.4.2 - Chân bàn",
            "steel_profile": "V50",
            "segment_name": "55.4.2.1",
            "length_mm": 660,
            "qty_segment_per_piece": 4,
        })
        spec.append("details", {
            "piece_name": "55.4.2 - Chân bàn",
            "steel_profile": "H25-50",
            "segment_name": "55.4.2.2",
            "length_mm": 200,
            "qty_segment_per_piece": 4,
        })
        
        spec.insert(ignore_permissions=True)
        frappe.db.set_value("Item", "J55.T4", "cutting_specification", spec.name)


def create_j55_variants():
    """
    Tạo Variant Items với quy tắc đặt tên:
    - Chung: J55.T4-DAY.<abbr>-MAT.<abbr>
    - Riêng: J55.T4-<CUST>-DAY.<abbr>-MAT.<abbr>
    """
    
    # Ghế variants: Wire Color + Cushion Color
    chair_variants = [
        {"wire": "Đen", "cushion": "Be", "customer": None}, # Chung
        {"wire": "Nâu", "cushion": "Đỏ", "customer": "VX"}, # Riêng Vidaxl
        {"wire": "Xám be", "cushion": "Be", "customer": "MY"}, # Riêng Meying
    ]
    
    # Bàn variants: Wire Color + Table Surface
    table_variants = [
        {"wire": "Đen", "surface": "Kính", "customer": None}, # Chung
        {"wire": "Nâu", "surface": "Gỗ", "customer": "GP"}, # Riêng Goplus
        {"wire": "Đen", "surface": "Kính", "customer": "MY"}, # Riêng Meying
    ]
    
    # Helper to get abbr
    def get_abbr(values_list, value):
        for v in values_list:
            if v["value"] == value:
                return v["abbr"]
        return value[:3].upper()
    
    # Create chair variants
    for v in chair_variants:
        wire_abbr = get_abbr(WIRE_COLORS, v["wire"])
        cushion_abbr = get_abbr(CUSHION_COLORS, v["cushion"])
        
        # Build variant code
        cust_part = f"-{v['customer']}" if v['customer'] else ""
        variant_code = f"J55.C{cust_part}-DAY.{wire_abbr}-NEM.{cushion_abbr}"
        
        if not frappe.db.exists("Item", variant_code):
            cust_name = f" ({v['customer']})" if v['customer'] else ""
            doc = frappe.new_doc("Item")
            doc.item_code = variant_code
            doc.item_name = f"Ghế JSE 55{cust_name} - Dây {v['wire']}, Nệm {v['cushion']}"
            doc.variant_of = "J55.C"
            doc.item_group = "Sản phẩm IEA"
            doc.stock_uom = "Cái"
            doc.is_stock_item = 1
            
            # Add attributes
            if v['customer']:
                doc.append("attributes", {"attribute": "Customer Code", "attribute_value": v['customer']})
            doc.append("attributes", {"attribute": "Wire Color", "attribute_value": v["wire"]})
            doc.append("attributes", {"attribute": "Cushion Color", "attribute_value": v["cushion"]})
            
            doc.insert(ignore_permissions=True)
    
    # Create table variants
    for v in table_variants:
        wire_abbr = get_abbr(WIRE_COLORS, v["wire"])
        surface_abbr = get_abbr(TABLE_SURFACES, v["surface"])
        
        # Build variant code
        cust_part = f"-{v['customer']}" if v['customer'] else ""
        variant_code = f"J55.T4{cust_part}-DAY.{wire_abbr}-MAT.{surface_abbr}"
        
        if not frappe.db.exists("Item", variant_code):
            cust_name = f" ({v['customer']})" if v['customer'] else ""
            doc = frappe.new_doc("Item")
            doc.item_code = variant_code
            doc.item_name = f"Bàn JSE 55{cust_name} - Dây {v['wire']}, Mặt {v['surface']}"
            doc.variant_of = "J55.T4"
            doc.item_group = "Sản phẩm IEA"
            doc.stock_uom = "Cái"
            doc.is_stock_item = 1
            
            # Add attributes
            if v['customer']:
                doc.append("attributes", {"attribute": "Customer Code", "attribute_value": v['customer']})
            doc.append("attributes", {"attribute": "Wire Color", "attribute_value": v["wire"]})
            doc.append("attributes", {"attribute": "Table Surface", "attribute_value": v["surface"]})
            
            doc.insert(ignore_permissions=True)
            
            # Case C: Creating separate cutting spec for Vidaxl (demo only)
            if v['customer'] == 'GP': # Goplus separate spec
                 create_custom_spec(variant_code, "Bàn J55 - Goplus")


def create_custom_spec(item_code, spec_name):
    """Helper để tạo Spec riêng cho variant (Case C)"""
    if not frappe.db.exists("Cutting Specification", {"spec_name": spec_name}):
        # Clone from standard J55.T4 spec for demo simplicity
        std_spec_name = "Bàn JSE 55 - 4 ghế"
        if frappe.db.exists("Cutting Specification", {"spec_name": std_spec_name}):
            std_spec = frappe.get_doc("Cutting Specification", {"spec_name": std_spec_name})
            new_spec = frappe.copy_doc(std_spec)
            new_spec.spec_name = spec_name
            new_spec.item_code = "" # Remove link to template if any
            new_spec.insert(ignore_permissions=True)
            
            frappe.db.set_value("Item", item_code, "cutting_specification", new_spec.name)


def create_customer_sku_mappings():
    """
    Tạo dữ liệu cho flow SKU khách → Variant Items:
    - Customer: LONGTECH INTERNATIONAL, VIDAXL, GOPLUS, MEYING
    - Mapping theo cases A, B, C
    """
    
    # 1. Tạo Customers
    customers = ["LONGTECH INTERNATIONAL", "VIDAXL", "GOPLUS", "MEYING"]
    for c_name in customers:
        if not frappe.db.exists("Customer", c_name):
            cust = frappe.new_doc("Customer")
            cust.customer_name = c_name
            cust.customer_type = "Company"
            cust.customer_group = "Commercial"
            cust.territory = "All Territories"
            cust.insert(ignore_permissions=True)
    
    # 2. Tạo Customer SKU Mappings
    sku_mappings = [
        # Case A: Chung (LONGTECH)
        {
            "customer_sku": "HW73186WH-12",
            "customer": "LONGTECH INTERNATIONAL",
            "item": "J55.T4-DAY.DEN-MAT.KINH",
            "barcode": "01445368",
            "description": "TABLE - Bàn JSE 55 (Chung)"
        },
        # Case B: Riêng phụ kiện/BOM (Meying) - Cùng Cutting Spec
        {
            "customer_sku": "MY-55-TABLE",
            "customer": "MEYING",
            "item": "J55.T4-MY-DAY.DEN-MAT.KINH",
            "barcode": "MY001",
            "description": "TABLE - Bàn JSE 55 (Meying BOM)"
        },
        # Case C: Riêng tất cả (Goplus) - Khác Cutting Spec
        {
            "customer_sku": "GP-55-TABLE",
            "customer": "GOPLUS",
            "item": "J55.T4-GP-DAY.NAU-MAT.GO",
            "barcode": "GP001",
            "description": "TABLE - Bàn JSE 55 (Goplus Spec)"
        },
        # Chair Variants
        {
            "customer_sku": "HW73186WH-22",
            "customer": "LONGTECH INTERNATIONAL",
            "item": "J55.C-DAY.DEN-NEM.BE",
            "barcode": "01445369",
            "description": "CHAIR - Ghế JSE 55 (Chung)"
        }
    ]
    
    for m in sku_mappings:
        if not frappe.db.exists("Customer SKU Mapping", m["customer_sku"]):
            mapping = frappe.new_doc("Customer SKU Mapping")
            mapping.customer_sku = m["customer_sku"]
            mapping.customer = m["customer"]
            mapping.item = m["item"]
            mapping.barcode = m.get("barcode")
            mapping.description = m["description"]
            mapping.insert(ignore_permissions=True)


@frappe.whitelist()
def test_flow():
    """Test full flow: Customer SKU → Item → Cutting Spec"""
    customer_sku = "HW73186WH-12"
    qty = 10  # Làm 10 cái
    
    # 1. Lookup Customer SKU Mapping
    mapping = frappe.db.get_value(
        "Customer SKU Mapping", 
        customer_sku, 
        ["item", "customer", "barcode"], 
        as_dict=True
    )
    
    if not mapping:
        return {"status": "error", "message": f"Không tìm thấy SKU: {customer_sku}"}
    
    # 2. Get Cutting Specification from Item
    spec_name = frappe.db.get_value("Item", mapping.item, "cutting_specification")
    
    result = {
        "customer_sku": customer_sku,
        "qty": qty,
        "customer": mapping.customer,
        "item": mapping.item,
        "cutting_specification": spec_name,
        "barcode": mapping.barcode
    }
    
    return result

