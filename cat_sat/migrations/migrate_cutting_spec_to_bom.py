# -*- coding: utf-8 -*-
"""
Migration script: Migrate Cutting Specification to BOM-linked design

This script:
1. For each existing Cutting Specification
2. Creates an Item for the product (if needed)
3. Creates Items for each piece in the spec (if needed)
4. Creates a BOM with pieces as items
5. Links the Cutting Spec to the Item

Run with:
    bench --site erp.dongnama.app console
    >>> from cat_sat.migrations.migrate_cutting_spec_to_bom import migrate_all
    >>> migrate_all()
"""
import frappe


def migrate_all(dry_run=True):
    """
    Migrate all existing Cutting Specifications to BOM-linked design.
    
    Args:
        dry_run: If True, only print what would be done without actual changes
    """
    specs = frappe.get_all("Cutting Specification", fields=["name", "spec_name"])
    
    print(f"Found {len(specs)} Cutting Specifications to migrate")
    
    for spec in specs:
        print(f"\n{'='*50}")
        print(f"Processing: {spec.name} - {spec.spec_name}")
        
        try:
            migrate_single_spec(spec.name, dry_run=dry_run)
        except Exception as e:
            print(f"ERROR migrating {spec.name}: {str(e)}")
            if not dry_run:
                frappe.db.rollback()
    
    if not dry_run:
        frappe.db.commit()
        print("\n✅ Migration completed and committed!")
    else:
        print("\n⚠️ DRY RUN - No changes made. Run with dry_run=False to apply.")


def migrate_single_spec(spec_name, dry_run=True):
    """Migrate a single Cutting Specification"""
    doc = frappe.get_doc("Cutting Specification", spec_name)
    
    # Check if already migrated
    if doc.linked_item:
        print(f"  Already migrated (linked_item: {doc.linked_item})")
        return
    
    # Get pieces from old table
    pieces = []
    if hasattr(doc, 'pieces') and doc.pieces:
        pieces = [(p.piece_name, p.piece_qty or 1) for p in doc.pieces if p.piece_name]
    
    if not pieces:
        print(f"  No pieces found in spec, skipping")
        return
    
    print(f"  Found {len(pieces)} pieces")
    
    # Create/get main product Item
    product_name = f"SP-{doc.spec_name}"
    product_item = get_or_create_item(product_name, doc.spec_name, "Products", dry_run)
    
    # Create/get Items for each piece
    piece_items = []
    for piece_name, piece_qty in pieces:
        piece_item_code = f"MANH-{doc.spec_name}-{piece_name}"
        piece_item = get_or_create_item(
            piece_item_code, 
            f"Mảnh {piece_name} - {doc.spec_name}",
            "Raw Material",
            dry_run
        )
        piece_items.append((piece_item, piece_qty, piece_name))
    
    # Create BOM
    bom_name = create_bom(product_item, piece_items, dry_run)
    
    # Update Cutting Specification
    if not dry_run:
        doc.linked_item = product_item
        doc.save()
        print(f"  ✅ Linked spec to {product_item}")
    else:
        print(f"  Would link spec to {product_item}")
    
    # Update details piece_name to match item_code
    update_details_piece_names(doc, piece_items, dry_run)


def get_or_create_item(item_code, item_name, item_group, dry_run):
    """Get existing item or create new one"""
    if frappe.db.exists("Item", item_code):
        print(f"    Item exists: {item_code}")
        return item_code
    
    if dry_run:
        print(f"    Would create Item: {item_code}")
        return item_code
    
    item = frappe.new_doc("Item")
    item.item_code = item_code
    item.item_name = item_name
    item.item_group = item_group
    item.stock_uom = "Nos"
    item.is_stock_item = 1
    item.save()
    print(f"    Created Item: {item_code}")
    return item_code


def create_bom(product_item, piece_items, dry_run):
    """Create BOM for product with pieces as items"""
    
    # Check if BOM already exists
    existing_bom = frappe.db.get_value("BOM", {
        "item": product_item,
        "is_active": 1,
        "is_default": 1
    }, "name")
    
    if existing_bom:
        print(f"    BOM exists: {existing_bom}")
        return existing_bom
    
    if dry_run:
        print(f"    Would create BOM for {product_item} with {len(piece_items)} items")
        return None
    
    bom = frappe.new_doc("BOM")
    bom.item = product_item
    bom.is_active = 1
    bom.is_default = 1
    
    for item_code, qty, piece_name in piece_items:
        bom.append("items", {
            "item_code": item_code,
            "qty": qty
        })
    
    bom.save()
    bom.submit()
    print(f"    Created BOM: {bom.name}")
    return bom.name


def update_details_piece_names(doc, piece_items, dry_run):
    """Update piece_name in details to match item_code"""
    
    # Build mapping: old_piece_name -> new_item_code
    name_map = {piece_name: item_code for item_code, qty, piece_name in piece_items}
    
    update_count = 0
    for detail in doc.details:
        if detail.piece_name in name_map:
            new_name = name_map[detail.piece_name]
            if dry_run:
                print(f"    Would update detail: {detail.piece_name} -> {new_name}")
            else:
                detail.piece_name = new_name
            update_count += 1
    
    if not dry_run and update_count > 0:
        doc.save()
        print(f"    Updated {update_count} detail piece names")


# Convenience functions
def migrate_cs00008():
    """Migrate only CS-00008 (for testing)"""
    migrate_single_spec("CS-00008", dry_run=False)


def dry_run_all():
    """Dry run migration for all specs"""
    migrate_all(dry_run=True)
