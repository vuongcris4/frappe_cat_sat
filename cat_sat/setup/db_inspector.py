"""
Database Inspector - Xem tổng quan database ERPNext
"""

import frappe
from frappe.utils import cstr
import json


def inspect_database(detailed=False):
    """
    Xem tổng quan database hiện tại
    
    Args:
        detailed: Nếu True, hiển thị chi tiết từng record
    """
    
    print("\n" + "="*80)
    print("DATABASE OVERVIEW - ERPNext Site: erp.dongnama.app")
    print("="*80 + "\n")
    
    # 1. Items
    print("📦 ITEMS")
    print("-" * 80)
    items = frappe.get_all("Item", 
        fields=["name", "item_name", "item_group", "stock_uom", "has_variants"],
        order_by="creation desc"
    )
    print(f"Total Items: {len(items)}\n")
    
    if detailed and items:
        print("Recent Items:")
        for item in items[:10]:
            print(f"  • {item.name}")
            print(f"    Name: {item.item_name}")
            print(f"    Group: {item.item_group}")
            print(f"    Variants: {'Yes' if item.has_variants else 'No'}")
            print()
    else:
        # Group by item_group
        groups = {}
        for item in items:
            group = item.item_group or "No Group"
            groups[group] = groups.get(group, 0) + 1
        
        print("By Item Group:")
        for group, count in sorted(groups.items(), key=lambda x: x[1], reverse=True):
            print(f"  {group}: {count}")
    
    print()
    
    # 2. Cutting Specifications
    print("✂️  CUTTING SPECIFICATIONS")
    print("-" * 80)
    specs = frappe.get_all("Cutting Specification",
        fields=["name", "spec_name"],
        order_by="creation desc"
    )
    print(f"Total Cutting Specs: {len(specs)}\n")
    
    if detailed and specs:
        print("Available Specs:")
        for spec in specs[:10]:
            # Get details count
            details = frappe.get_all("Cutting Detail",
                filters={"parent": spec.name},
                fields=["steel_profile", "length_mm"]
            )
            steel_types = set(d.steel_profile for d in details if d.steel_profile)
            
            print(f"  • {spec.name}")
            print(f"    Name: {spec.spec_name}")
            print(f"    Segments: {len(details)}")
            print(f"    Steel Types: {', '.join(steel_types) if steel_types else 'N/A'}")
            print()
    else:
        print("Specs:", ", ".join([s.name for s in specs[:20]]))
        if len(specs) > 20:
            print(f"... and {len(specs) - 20} more")
    
    print()
    
    # 3. Steel Profiles
    print("🔩 STEEL PROFILES")
    print("-" * 80)
    profiles = frappe.get_all("Steel Profile",
        fields=["profile_code", "shape", "dimension"],
        order_by="profile_code"
    )
    print(f"Total Steel Profiles: {len(profiles)}\n")
    
    if profiles:
        print("Available Profiles:")
        for prof in profiles:
            print(f"  • {prof.profile_code} ({prof.shape}{prof.dimension})")
    
    print()
    
    # 4. Customers
    print("👥 CUSTOMERS")
    print("-" * 80)
    customers = frappe.get_all("Customer",
        fields=["name", "customer_name", "customer_group"],
        order_by="name"
    )
    print(f"Total Customers: {len(customers)}\n")
    
    if customers:
        for cust in customers[:10]:
            print(f"  • {cust.name} ({cust.customer_group})")
        if len(customers) > 10:
            print(f"  ... and {len(customers) - 10} more")
    
    print()
    
    # 5. Item Groups
    print("📁 ITEM GROUPS")
    print("-" * 80)
    item_groups = frappe.get_all("Item Group",
        fields=["name", "parent_item_group", "is_group"],
        order_by="name"
    )
    print(f"Total Item Groups: {len(item_groups)}\n")
    
    # Build tree
    tree = {}
    for grp in item_groups:
        parent = grp.parent_item_group
        if parent not in tree:
            tree[parent] = []
        tree[parent].append(grp.name)
    
    def print_tree(node, indent=0):
        if node in tree:
            for child in sorted(tree[node]):
                print("  " * indent + f"├─ {child}")
                print_tree(child, indent + 1)
    
    print("Item Group Hierarchy:")
    print_tree("All Item Groups")
    
    print()
    
    # 6. Cutting Plans
    print("📋 CUTTING PLANS")
    print("-" * 80)
    plans = frappe.get_all("Cutting Plan",
        fields=["name", "plan_date", "status"],
        order_by="creation desc"
    )
    print(f"Total Cutting Plans: {len(plans)}\n")
    
    if plans:
        print("Recent Plans:")
        for plan in plans[:5]:
            print(f"  • {plan.name} - {plan.status} ({plan.plan_date})")
    
    print()
    
    # 7. Cutting Orders
    print("🔪 CUTTING ORDERS")
    print("-" * 80)
    orders = frappe.get_all("Cutting Order",
        fields=["name", "cutting_plan", "steel_profile", "status"],
        order_by="creation desc"
    )
    print(f"Total Cutting Orders: {len(orders)}\n")
    
    if orders:
        print("Recent Orders:")
        for order in orders[:5]:
            print(f"  • {order.name} ({order.steel_profile}) - {order.status}")
    
    print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Items: {len(items)}")
    print(f"Cutting Specifications: {len(specs)}")
    print(f"Steel Profiles: {len(profiles)}")
    print(f"Customers: {len(customers)}")
    print(f"Item Groups: {len(item_groups)}")
    print(f"Cutting Plans: {len(plans)}")
    print(f"Cutting Orders: {len(orders)}")
    print("="*80 + "\n")
    
    return {
        "items": len(items),
        "specs": len(specs),
        "profiles": len(profiles),
        "customers": len(customers),
        "item_groups": len(item_groups),
        "plans": len(plans),
        "orders": len(orders)
    }


def show_items_by_group(group_name=None):
    """Xem items theo group cụ thể"""
    
    if group_name:
        filters = {"item_group": group_name}
        print(f"\n📦 Items in '{group_name}':")
    else:
        filters = {}
        print(f"\n📦 All Items:")
    
    print("-" * 80)
    
    items = frappe.get_all("Item",
        filters=filters,
        fields=["name", "item_name", "item_group", "cutting_specification"],
        order_by="item_group, name"
    )
    
    for item in items:
        spec_info = f" → Spec: {item.cutting_specification}" if item.cutting_specification else ""
        print(f"  • [{item.item_group}] {item.name}")
        print(f"    {item.item_name}{spec_info}")
    
    print(f"\nTotal: {len(items)} items\n")
    
    return items


def show_cutting_spec_details(spec_name):
    """Xem chi tiết 1 cutting spec"""
    
    spec = frappe.get_doc("Cutting Specification", spec_name)
    
    print(f"\n✂️  Cutting Specification: {spec.spec_name}")
    print("="*80)
    
    print("\n📦 Pieces:")
    for piece in spec.pieces:
        print(f"  • {piece.piece_code} - {piece.piece_name} (Qty: {piece.piece_qty})")
    
    print("\n🔧 Segments:")
    for detail in spec.details:
        print(f"  • {detail.segment_name} ({detail.steel_profile})")
        print(f"    Length: {detail.length_mm}mm")
        print(f"    Qty per piece: {detail.qty_segment_per_piece}")
        if detail.note:
            print(f"    Note: {detail.note}")
        print()
    
    return spec


def quick_stats():
    """Quick stats"""
    
    print("\n" + "="*80)
    print("QUICK STATS")
    print("="*80 + "\n")
    
    stats = {}
    
    # Count by doctype
    doctypes = [
        "Item",
        "Cutting Specification", 
        "Steel Profile",
        "Customer",
        "Cutting Plan",
        "Cutting Order",
        "Item Group"
    ]
    
    for dt in doctypes:
        count = frappe.db.count(dt)
        stats[dt] = count
        print(f"{dt:.<40} {count:>5}")
    
    print("="*80 + "\n")
    
    return stats


# Quick access functions
def db():
    """Alias cho inspect_database()"""
    return inspect_database()

def items(group=None):
    """Alias cho show_items_by_group()"""
    return show_items_by_group(group)

def spec(name):
    """Alias cho show_cutting_spec_details()"""
    return show_cutting_spec_details(name)

def stats():
    """Alias cho quick_stats()"""
    return quick_stats()
