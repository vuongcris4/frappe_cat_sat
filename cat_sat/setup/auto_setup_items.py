#!/usr/bin/env python3
"""
Auto-setup Item Organization
Run this script to automatically setup Item Groups and migrate items

Usage:
    cd /home/trand/frappe/sites/erp.dongnama.app/workspace/frappe-bench
    bench --site erp.dongnama.app execute cat_sat.setup.auto_setup_items
"""

import frappe
from cat_sat.setup.item_organization import setup_item_groups, add_custom_fields, migrate_existing_items


def auto_setup(dry_run=False):
    """
    Auto-setup Item Groups, Custom Fields, and migrate items
    
    Args:
        dry_run: If False, actually apply changes. If True, only preview.
    """
    
    print("\n" + "="*80)
    print("AUTO SETUP ITEM ORGANIZATION")
    print("="*80)
    print(f"Mode: {'DRY RUN (Preview)' if dry_run else 'LIVE (Apply Changes)'}")
    print("="*80 + "\n")
    
    try:
        # Step 1: Setup Item Groups
        print("[1/3] Creating Item Groups...")
        print("-" * 80)
        result1 = setup_item_groups()
        print(f"✅ Item Groups: {result1['created']} created, {result1['skipped']} skipped\n")
        
        # Step 2: Add Custom Fields
        print("[2/3] Adding Custom Fields...")
        print("-" * 80)
        result2 = add_custom_fields()
        if result2:
            print("✅ Custom Fields added successfully\n")
        else:
            print("⚠️  Custom Fields already exist or error occurred\n")
        
        # Step 3: Migrate Items
        print(f"[3/3] Migrating Existing Items {'(DRY RUN)' if dry_run else '(LIVE)'}...")
        print("-" * 80)
        result3 = migrate_existing_items(dry_run=dry_run)
        print(f"✅ Migration: {result3['updated']} items updated, {result3['skipped']} skipped\n")
        
        # Summary
        print("="*80)
        print("SETUP COMPLETE!")
        print("="*80)
        print(f"Item Groups Created:  {result1['created']}")
        print(f"Items Migrated:       {result3['updated']}")
        
        if dry_run:
            print("\n⚠️  THIS WAS A DRY RUN - No changes were saved to database")
            print("\nTo apply changes, run:")
            print("  bench --site erp.dongnama.app execute cat_sat.setup.auto_setup_items.apply_changes")
        else:
            print("\n✅ All changes have been applied to database!")
            print("\nNext steps:")
            print("  1. Refresh your Item List page")
            print("  2. Try filtering by Customer or Item Category")
            print("  3. Check that Item Groups look correct")
        
        print("="*80 + "\n")
        
        return {
            "success": True,
            "item_groups": result1,
            "migration": result3
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def preview():
    """Preview changes without applying"""
    return auto_setup(dry_run=True)


def apply_changes():
    """Apply changes to database"""
    return auto_setup(dry_run=False)


# Default: Run preview
if __name__ == "__main__":
    preview()
