"""
Bulk Auto Import - Tự động import tất cả data từ Excel
Không cần làm gì thủ công!

Chỉ cần:
1. Upload file Excel vào thư mục
2. Chạy script này
3. Done!
"""

import frappe
import os
from cat_sat.setup.import_from_excel import import_bom_excel


def find_excel_files(search_paths=None):
    """
    Tìm tất cả file Excel trong các thư mục
    """
    
    if search_paths is None:
        search_paths = [
            '/home/trand/Downloads',
            '/home/trand/Desktop',
            '/home/trand/Documents',
            '/tmp',
        ]
    
    excel_files = []
    
    for path in search_paths:
        if not os.path.exists(path):
            continue
        
        print(f"🔍 Scanning: {path}")
        
        for file in os.listdir(path):
            if file.endswith(('.xlsx', '.xls')) and not file.startswith('~'):
                full_path = os.path.join(path, file)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                excel_files.append({
                    'path': full_path,
                    'name': file,
                    'size_mb': round(size_mb, 2)
                })
    
    return excel_files


def auto_import_all(file_path=None, dry_run=True):
    """
    Tự động import tất cả Excel files
    
    Args:
        file_path: Nếu chỉ định path cụ thể, chỉ import file đó
        dry_run: Preview trước khi apply
    """
    
    print("\n" + "="*80)
    print("BULK AUTO IMPORT - IMPORT TẤT CẢ DATA")
    print("="*80)
    print(f"Mode: {'DRY RUN (Preview)' if dry_run else 'LIVE (Apply)'}")
    print("="*80 + "\n")
    
    if file_path:
        # Import 1 file cụ thể
        files_to_import = [{'path': file_path, 'name': os.path.basename(file_path)}]
    else:
        # Tìm tất cả Excel files
        print("🔍 Tìm kiếm Excel files...\n")
        files_to_import = find_excel_files()
    
    if not files_to_import:
        print("❌ Không tìm thấy file Excel nào!")
        print("\nVui lòng:")
        print("  1. Upload file Excel vào /home/trand/Downloads")
        print("  2. Hoặc chỉ định path: auto_import_all('/path/to/file.xlsx')")
        return {"success": False, "error": "No Excel files found"}
    
    print(f"📋 Tìm thấy {len(files_to_import)} file(s):\n")
    for idx, f in enumerate(files_to_import, 1):
        print(f"  {idx}. {f['name']} ({f.get('size_mb', 0)}MB)")
    print()
    
    # Import từng file
    results = []
    
    for idx, file_info in enumerate(files_to_import, 1):
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(files_to_import)}] Processing: {file_info['name']}")
        print('='*80)
        
        try:
            result = import_bom_excel(file_info['path'], dry_run=dry_run)
            results.append({
                'file': file_info['name'],
                'success': result.get('success', False),
                'products': result.get('products', 0),
                'specs_created': result.get('specs_created', 0),
                'items_created': result.get('items_created', 0),
                'error': result.get('error')
            })
        except Exception as e:
            print(f"❌ Error processing {file_info['name']}: {str(e)}")
            results.append({
                'file': file_info['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("BULK IMPORT SUMMARY")
    print("="*80)
    
    total_products = sum(r.get('products', 0) for r in results)
    total_specs = sum(r.get('specs_created', 0) for r in results)
    total_items = sum(r.get('items_created', 0) for r in results)
    success_count = sum(1 for r in results if r.get('success'))
    
    print(f"Files processed: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    print(f"\nTotal products: {total_products}")
    print(f"Total specs created: {total_specs}")
    print(f"Total items created: {total_items}")
    
    if dry_run:
        print("\n⚠️  THIS WAS A DRY RUN")
        print("To apply changes, run:")
        if file_path:
            print(f"  auto_import_all('{file_path}', dry_run=False)")
        else:
            print("  auto_import_all(dry_run=False)")
    else:
        print("\n✅ ALL DATA IMPORTED!")
    
    print("="*80 + "\n")
    
    # Details
    if not dry_run:
        print("📊 Details:\n")
        for r in results:
            status = "✅" if r.get('success') else "❌"
            print(f"{status} {r['file']}")
            if r.get('success'):
                print(f"   Products: {r.get('products', 0)}, Specs: {r.get('specs_created', 0)}, Items: {r.get('items_created', 0)}")
            else:
                print(f"   Error: {r.get('error', 'Unknown')}")
        print()
    
    return {
        "success": success_count > 0,
        "total_files": len(results),
        "successful_files": success_count,
        "total_products": total_products,
        "total_specs": total_specs,
        "total_items": total_items,
        "results": results
    }


def quick_import_from_uploaded(filename=None):
    """
    Quick import từ file vừa upload
    
    Usage:
        1. Upload file lên /home/trand/Downloads/your_file.xlsx
        2. Chạy: quick_import_from_uploaded('your_file.xlsx')
    """
    
    if filename:
        path = f'/home/trand/Downloads/{filename}'
    else:
        # Tìm file mới nhất
        downloads = '/home/trand/Downloads'
        excel_files = [f for f in os.listdir(downloads) if f.endswith(('.xlsx', '.xls'))]
        
        if not excel_files:
            print("❌ No Excel files in Downloads")
            return
        
        # Sort by modification time, get latest
        excel_files.sort(key=lambda f: os.path.getmtime(os.path.join(downloads, f)), reverse=True)
        filename = excel_files[0]
        path = os.path.join(downloads, filename)
    
    print(f"📂 File: {filename}\n")
    
    # Preview
    print("STEP 1: PREVIEW\n")
    result = import_bom_excel(path, dry_run=True)
    
    if result.get('success'):
        print("\n✅ Preview OK!")
        print("\nĐể apply, chạy:")
        print(f"  import_bom_excel('{path}', dry_run=False)")
    
    return result


# Convenience function
def import_now(file_path):
    """Import ngay lập tức mà không preview"""
    return auto_import_all(file_path, dry_run=False)
