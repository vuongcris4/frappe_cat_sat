"""
Cutting Plan Service
Updated for IEA design - uses pieces table and new field names
"""
import frappe


def get_optimizer_input(plan_name: str) -> dict:
    plan = frappe.get_doc("Cutting Plan", plan_name)
    demand = {}

    for row in plan.requirements:
        key = (row.steel_profile, row.length_mm)
        demand[key] = demand.get(key, 0) + row.qty

    return demand


def get_cutting_spec_for_item(item_code: str) -> str:
    """
    Get Cutting Specification for an Item.
    
    Logic:
    1. First check if Item has cutting_specification set directly
    2. If not, check if Item has factory_code and get spec from factory_code Item
    3. If factory_code Item has cutting_specification, use that
    
    This supports 2-layer model: SKU Item → factory_code → Cutting Spec
    """
    # Check direct cutting_specification
    item_data = frappe.db.get_value("Item", item_code, 
                                     ["cutting_specification", "factory_code"], 
                                     as_dict=True)
    
    if not item_data:
        return None
    
    # Direct spec on item
    if item_data.get("cutting_specification"):
        return item_data["cutting_specification"]
    
    # Fallback: Check factory_code
    factory_code = item_data.get("factory_code")
    if factory_code and frappe.db.exists("Item", factory_code):
        factory_spec = frappe.db.get_value("Item", factory_code, "cutting_specification")
        if factory_spec:
            return factory_spec
    
    # Lookup by item_template field on Cutting Specification
    # This is the standard way - Cutting Specification has item_template linking to Item
    spec = frappe.db.get_value(
        "Cutting Specification",
        {"item_template": item_code},
        "name"
    )
    if spec:
        return spec
    
    return None


@frappe.whitelist()
def generate_requirements(plan):
    """Generate cutting requirements from plan items using Cutting Specification"""
    # Clear existing requirements
    plan.set("requirements", [])
    
    # Cache for Item names to avoid repeated DB lookups
    item_name_cache = {}
    
    # Piece quantities mapping for I5 (hardcoded from master reference)
    piece_qty_map = {
        # I5: 1 ghế đôi + 2 ghế đơn + 1 bàn
        "PHOI-I5.1.1": 1, "PHOI-I5.1.2": 1, "PHOI-I5.1.3": 1, "PHOI-I5.1.4": 1,  # Ghế đôi x1
        "PHOI-I5.2.1": 2, "PHOI-I5.2.2": 2, "PHOI-I5.2.3": 2, "PHOI-I5.2.4": 2,  # Ghế đơn x2
        "PHOI-I5.3.1": 1, "PHOI-I5.3.2": 2,  # Bàn: 1 chân + 2 hông
        # I3: 2 ghế + 1 bàn
        "PHOI-I3.1.1": 2, "PHOI-I3.1.2": 2, "PHOI-I3.1.3": 2, "PHOI-I3.1.4": 2,  # Ghế x2
        "PHOI-I3.2.1": 1, "PHOI-I3.2.2": 2, "PHOI-I3.2.3": 2,  # Bàn
    }
    
    # Aggregation key: (steel_profile, length_mm, segment_name)
    aggregated_requirements = {}

    for row in plan.items:
        spec_name = get_cutting_spec_for_item(row.item_code)

        if not spec_name:
            frappe.throw(f"Thành phẩm {row.item_code} chưa được gán Bảng cắt sắt (kiểm tra cutting_specification hoặc factory_code)")
            
        spec = frappe.get_doc("Cutting Specification", spec_name)
        
        product_qty = int(row.product_qty)

        for d in spec.details:
            bom_item = d.bom_item  # e.g., "PHOI-I5.1.1"
            if not bom_item:
                continue
            
            # Get piece_name from Item's custom field (with cache)
            if bom_item not in item_name_cache:
                item_piece_name = frappe.db.get_value("Item", bom_item, "piece_name")
                # Just use the short name (e.g., "Khung tựa đôi")
                item_name_cache[bom_item] = item_piece_name or bom_item
            piece_name = item_name_cache[bom_item]
            
            # Get piece_qty from mapping, or default to 1
            piece_qty = piece_qty_map.get(bom_item, 1)
            
            # Total segments for this entry
            qty_per_unit = getattr(d, 'qty_per_unit', 1) or 1
            total_segment = int(qty_per_unit) * int(piece_qty) * product_qty

            if total_segment > 0:
                segment_name = d.segment_name or f"{d.steel_profile}"
                
                # Aggregation Key: (steel_profile, length_mm, segment_name)
                agg_key = (d.steel_profile, d.length_mm, segment_name)
                
                if agg_key not in aggregated_requirements:
                    aggregated_requirements[agg_key] = {
                        "qty": 0,
                        "piece_code": bom_item,
                        "piece_name": piece_name
                    }
                aggregated_requirements[agg_key]["qty"] += total_segment

    # Add to child table
    for (steel_profile, length_mm, segment_name), data in aggregated_requirements.items():
        plan.append("requirements", {
            "steel_profile": steel_profile,
            "length_mm": length_mm,
            "qty": data["qty"],
            "segment_name": segment_name,
            "piece_code": data["piece_code"],
            "piece_name": data["piece_name"]
        })


@frappe.whitelist()
def generate_requirements_from_plan(plan_name: str):
    """Wrapper for API compatibility"""
    plan = frappe.get_doc("Cutting Plan", plan_name)
    generate_requirements(plan)
    plan.save()


@frappe.whitelist()
def create_cutting_orders(plan_name: str):
    """Create Cutting Orders from Cutting Plan, grouped by steel_profile"""
    plan = frappe.get_doc("Cutting Plan", plan_name)
    
    if not plan.requirements:
        frappe.throw("Vui lòng tạo danh sách yêu cầu cắt trước (Bấm Save)")

    # Group by steel_profile
    grouped_reqs = {}
    for row in plan.requirements:
        if row.steel_profile not in grouped_reqs:
            grouped_reqs[row.steel_profile] = []
        grouped_reqs[row.steel_profile].append(row)

    created_orders = []

    for steel_profile, rows in grouped_reqs.items():
        # Check if exists
        exists = frappe.db.exists("Cutting Order", {
            "cutting_plan": plan.name,
            "steel_profile": steel_profile
        })
        
        if exists:
            continue

        # Get default trim from Cutting Settings
        settings = frappe.get_single("Cutting Settings")
        default_trim = settings.laser_trim_cut or 10

        # Create new Order
        co = frappe.new_doc("Cutting Order")
        co.cutting_plan = plan.name
        co.steel_profile = steel_profile
        co.stock_length = 6000  # Default, should ideally come from Steel Profile
        co.trim_cut = default_trim  # Set default trim from settings
        
        for r in rows:
            co.append("items", {
                "length_mm": r.length_mm,
                "qty": r.qty,
                "segment_name": r.segment_name,
                "piece_code": getattr(r, 'piece_code', '') or '',
                "piece_name": getattr(r, 'piece_name', '') or ''
            })
            
        co.insert()
        created_orders.append(co.name)
        
    if created_orders:
        frappe.msgprint(f"Đã tạo {len(created_orders)} Lệnh cắt: {', '.join(created_orders)}")
    else:
        frappe.msgprint("Không có Lệnh cắt nào mới được tạo (có thể đã tồn tại).")

    return created_orders
