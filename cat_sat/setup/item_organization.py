"""
Setup Item Groups and Custom Fields for Better Item Organization

This script creates:
1. Item Group hierarchy (Nguyên Liệu/Thành Phẩm/Bán Thành Phẩm)
2. Custom fields for Item doctype (Customer, Product Line, etc.)
3. Migration script to update existing items

Usage:
    bench --site [site-name] execute cat_sat.setup.item_organization.setup_item_groups
    bench --site [site-name] execute cat_sat.setup.item_organization.add_custom_fields
    bench --site [site-name] execute cat_sat.setup.item_organization.migrate_existing_items
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_item_groups():
    """Create Item Group hierarchy for better organization"""
    
    print("Creating Item Group hierarchy...")
    
    groups = [
        # Nguyên Liệu - Simplified (chỉ Thép Ống, không phân loại chi tiết)
        {
            "name": "Nguyên Liệu",
            "parent": "All Item Groups",
            "is_group": 1
        },
        {
            "name": "Thép Ống",
            "parent": "Nguyên Liệu",
            "is_group": 0  # Không cần sub-categories
        },
        {
            "name": "Phụ Kiện",
            "parent": "Nguyên Liệu",
            "is_group": 0
        },
        
        # Thành Phẩm - Phân loại theo Loại sản phẩm > Customer
        {
            "name": "Thành Phẩm",
            "parent": "All Item Groups",
            "is_group": 1
        },
        
        # === GHẾ ===
        {
            "name": "Ghế",
            "parent": "Thành Phẩm",
            "is_group": 1
        },
        {
            "name": "Ghế - IEA",
            "parent": "Ghế",
            "is_group": 1
        },
        {
            "name": "Ghế - JSE 55",
            "parent": "Ghế - IEA",
            "is_group": 0
        },
        {
            "name": "Ghế - JSE 73",
            "parent": "Ghế - IEA",
            "is_group": 0
        },
        {
            "name": "Ghế - GOPLUS",
            "parent": "Ghế",
            "is_group": 0
        },
        
        # === BÀN ===
        {
            "name": "Bàn",
            "parent": "Thành Phẩm",
            "is_group": 1
        },
        {
            "name": "Bàn - IEA",
            "parent": "Bàn",
            "is_group": 0
        },
        {
            "name": "Bàn - GOPLUS",
            "parent": "Bàn",
            "is_group": 0
        },
        
        # === BỘ (COMBO) ===
        {
            "name": "Bộ",
            "parent": "Thành Phẩm",
            "is_group": 1
        },
        {
            "name": "Bộ - IEA",
            "parent": "Bộ",
            "is_group": 0
        },
        {
            "name": "Bộ - GOPLUS",
            "parent": "Bộ",
            "is_group": 0
        },
        
        # Bán Thành Phẩm (Optional - nếu cần)
        {
            "name": "Bán Thành Phẩm",
            "parent": "All Item Groups",
            "is_group": 1
        },
        {
            "name": "Mảnh",
            "parent": "Bán Thành Phẩm",
            "is_group": 0
        },
    ]
    
    created_count = 0
    skipped_count = 0
    
    for group_data in groups:
        group_name = group_data["name"]
        
        if frappe.db.exists("Item Group", group_name):
            print(f"  ⏭️  Skipped: {group_name} (already exists)")
            skipped_count += 1
            continue
        
        try:
            doc = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": group_name,
                "parent_item_group": group_data["parent"],
                "is_group": group_data.get("is_group", 0)
            })
            doc.insert(ignore_permissions=True)
            created_count += 1
            print(f"  ✅ Created: {group_name}")
        except Exception as e:
            print(f"  ❌ Error creating {group_name}: {str(e)}")
    
    frappe.db.commit()
    print(f"\n✅ Done! Created {created_count} groups, skipped {skipped_count} existing groups.")
    return {"created": created_count, "skipped": skipped_count}


def add_custom_fields():
    """Add custom fields to Item doctype"""
    
    print("Adding custom fields to Item...")
    
    custom_fields = {
        "Item": [
            {
                "fieldname": "item_classification_section",
                "label": "Item Classification",
                "fieldtype": "Section Break",
                "insert_after": "item_group",
                "collapsible": 0
            },
            {
                "fieldname": "customer",
                "label": "Customer",
                "fieldtype": "Link",
                "options": "Customer",
                "insert_after": "item_classification_section",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "translatable": 0,
                "description": "Customer for this product (e.g., IEA, GOPLUS)"
            },
            {
                "fieldname": "product_line",
                "label": "Product Line",
                "fieldtype": "Data",
                "insert_after": "customer",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "translatable": 0,
                "description": "Product line/series (e.g., JSE 55, JSE 73, HW731)"
            },
            {
                "fieldname": "column_break_item_class",
                "fieldtype": "Column Break",
                "insert_after": "product_line"
            },
            {
                "fieldname": "item_category",
                "label": "Item Category",
                "fieldtype": "Select",
                "options": "\nGhế\nBàn\nBộ (Combo)\nMảnh\nNguyên Liệu\nPhụ Kiện",
                "insert_after": "column_break_item_class",
                "in_standard_filter": 1,
                "translatable": 0,
                "description": "Category of item"
            },
            {
                "fieldname": "steel_types_used",
                "label": "Steel Types Used",
                "fieldtype": "Small Text",
                "insert_after": "item_category",
                "translatable": 0,
                "description": "Steel profiles used in this product (e.g., Fi21, V12)"
            },
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("✅ Custom fields added successfully!")
        return True
    except Exception as e:
        print(f"❌ Error adding custom fields: {str(e)}")
        frappe.db.rollback()
        return False


def migrate_existing_items(dry_run=True):
    """
    Migrate existing items to new structure
    
    Args:
        dry_run: If True, only print what would be changed without saving
    """
    
    print(f"\n{'DRY RUN - ' if dry_run else ''}Migrating existing items...")
    print("=" * 60)
    
    items = frappe.get_all(
        "Item",
        fields=["name", "item_name", "item_code", "item_group"],
        order_by="name"
    )
    
    updated_count = 0
    skipped_count = 0
    
    for item_data in items:
        try:
            doc = frappe.get_doc("Item", item_data.name)
            original_group = doc.item_group
            changes = {}
            
            item_name = item_data.item_name or ""
            item_code = item_data.name
            
            # Detect IEA products (JSE 55, JSE 73, etc.)
            if "JSE 55" in item_name or "J55" in item_code:
                changes["customer"] = "IEA"
                changes["product_line"] = "JSE 55"
                
                if "Ghế" in item_name or any(x in item_name for x in ["MY", "VX"]):
                    changes["item_group"] = "Ghế - JSE 55"
                    changes["item_category"] = "Ghế"
                elif "Bàn" in item_name:
                    changes["item_group"] = "Bàn - IEA"
                    changes["item_category"] = "Bàn"
                elif "Bộ" in item_name or "LONGTECH" in item_name:
                    changes["item_group"] = "Bộ - IEA"
                    changes["item_category"] = "Bộ"
                else:
                    # Default to Ghế if unsure
                    changes["item_group"] = "Ghế - JSE 55"
                    changes["item_category"] = "Ghế"
                    
            elif "JSE 73" in item_name or "J73" in item_code:
                changes["item_group"] = "Ghế - JSE 73"
                changes["customer"] = "IEA"
                changes["product_line"] = "JSE 73"
                changes["item_category"] = "Ghế"
                
            elif "GOPLUS" in item_name or "GP" in item_code:
                changes["customer"] = "GOPLUS"
                
                if "Ghế" in item_name:
                    changes["item_group"] = "Ghế - GOPLUS"
                    changes["item_category"] = "Ghế"
                elif "Bàn" in item_name:
                    changes["item_group"] = "Bàn - GOPLUS"
                    changes["item_category"] = "Bàn"
                elif "Bộ" in item_name:
                    changes["item_group"] = "Bộ - GOPLUS"
                    changes["item_category"] = "Bộ"
                else:
                    # Default
                    changes["item_group"] = "Ghế - GOPLUS"
                    changes["item_category"] = "Ghế"
                    
            # Detect steel/raw materials - Simplified (chỉ "Thép Ống")
            elif any(x in item_code for x in ["TUBE-STEEL", "SÀ-", "Fi", "V12", "H10", "SAL-"]):
                changes["item_category"] = "Nguyên Liệu"
                changes["item_group"] = "Thép Ống"  # Tất cả sắt đều vào "Thép Ống"
            
            # Auto-fill steel types from cutting specification
            if doc.get("cutting_specification"):
                try:
                    spec = frappe.get_doc("Cutting Specification", doc.cutting_specification)
                    steel_types = set()
                    
                    for detail in spec.details:
                        if detail.steel_profile:
                            steel_types.add(detail.steel_profile)
                    
                    if steel_types:
                        changes["steel_types_used"] = ", ".join(sorted(steel_types))
                except Exception:
                    pass  # Skip if spec not found
            
            # Apply changes
            if changes:
                if dry_run:
                    print(f"\n📝 Would update: {item_code}")
                    print(f"   Name: {item_name[:50]}")
                    for field, value in changes.items():
                        old_value = getattr(doc, field, None)
                        if old_value != value:
                            print(f"   {field}: '{old_value}' → '{value}'")
                else:
                    for field, value in changes.items():
                        setattr(doc, field, value)
                    doc.save(ignore_permissions=True)
                    print(f"✅ Updated: {item_code} → {changes.get('item_group', original_group)}")
                
                updated_count += 1
            else:
                skipped_count += 1
                
        except Exception as e:
            print(f"❌ Error processing {item_data.name}: {str(e)}")
    
    if not dry_run:
        frappe.db.commit()
    
    print("\n" + "=" * 60)
    print(f"{'DRY RUN - ' if dry_run else ''}Summary:")
    print(f"  Items to update: {updated_count}")
    print(f"  Items skipped: {skipped_count}")
    print(f"  Total items: {len(items)}")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN. No changes were saved.")
        print("   Run with dry_run=False to apply changes.")
    else:
        print("\n✅ Migration completed!")
    
    return {"updated": updated_count, "skipped": skipped_count}


def run_full_setup(dry_run_migration=True):
    """
    Run complete setup:
    1. Create Item Groups
    2. Add Custom Fields
    3. Migrate existing items
    """
    
    print("\n" + "=" * 60)
    print("ITEM ORGANIZATION SETUP")
    print("=" * 60)
    
    # Step 1: Create Item Groups
    print("\n[1/3] Setting up Item Groups...")
    setup_item_groups()
    
    # Step 2: Add Custom Fields
    print("\n[2/3] Adding Custom Fields...")
    add_custom_fields()
    
    # Step 3: Migrate Existing Items
    print(f"\n[3/3] Migrating Existing Items (dry_run={dry_run_migration})...")
    migrate_existing_items(dry_run=dry_run_migration)
    
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    
    if dry_run_migration:
        print("\n⚠️  Migration was run in DRY RUN mode.")
        print("To apply changes, run:")
        print("  bench --site [site] execute cat_sat.setup.item_organization.migrate_existing_items --kwargs \"{'dry_run': False}\"")


# Convenience function for benching running individual steps
def setup():
    """Quick setup - creates groups and fields only"""
    setup_item_groups()
    add_custom_fields()
    print("\n✅ Item Groups and Custom Fields created!")
    print("Next: Review and run migration:")
    print("  bench --site [site] execute cat_sat.setup.item_organization.migrate_existing_items")
