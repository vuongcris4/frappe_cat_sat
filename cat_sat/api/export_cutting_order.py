"""
Export Cutting Order to Excel with linked formulas
"""
import frappe
import re
from io import BytesIO


def parse_segments_summary(summary):
    """Parse '3x H10-20 (uốn) 497mm [Khung tựa], ...' into dict"""
    segments = {}
    parts = summary.split(", ")
    for part in parts:
        # Match: NUMBERx SEGMENT_NAME LENGTHmm [PIECE_NAME]
        match = re.match(r"(\d+)x\s+(.+?)\s+(\d+)mm\s+\[(.+?)\]", part)
        if match:
            count = int(match.group(1))
            segment_name = match.group(2)
            length = int(match.group(3))
            piece_name = match.group(4)
            # Create unique key
            key = f"{segment_name}_{length}_{piece_name}"
            segments[key] = count
    return segments


def get_column_letter(col_idx):
    """Convert 0-indexed column number to Excel column letter (A, B, ..., Z, AA, AB, ...)"""
    result = ""
    while col_idx >= 0:
        result = chr(col_idx % 26 + ord('A')) + result
        col_idx = col_idx // 26 - 1
    return result


@frappe.whitelist()
def export_cutting_order_excel(cutting_order_name):
    """
    Export Cutting Order to Excel with:
    - Sheet 1: Chi tiết cắt (with auto-calculated 'Số lượng đã cắt')
    - Sheet 2: Kết quả tối ưu (with input column for 'SL đã cắt')
    
    Ma trận hệ số được đặt trong các cột ẩn của sheet Chi tiết cắt
    """
    try:
        import pandas as pd
    except ImportError:
        frappe.throw("pandas library is required")
    
    # Get Cutting Order
    co = frappe.get_doc("Cutting Order", cutting_order_name)
    items = co.items
    patterns = co.optimization_result
    
    if not items:
        frappe.throw("Cutting Order has no items")
    
    if not patterns:
        frappe.throw("Cutting Order has no optimization result")
    
    # Build unique segment keys for each item
    item_keys = []
    for item in items:
        key = f"{item.segment_name}_{item.length_mm}_{item.piece_name}"
        item_keys.append(key)
    
    # Build pattern segment data
    pattern_segments = []
    for pat in patterns:
        segs = parse_segments_summary(pat.segments_summary)
        pattern_segments.append(segs)
    
    # Create the count matrix (items x patterns)
    count_matrix = []
    for key in item_keys:
        row = []
        for segs in pattern_segments:
            count = segs.get(key, 0)
            row.append(count)
        count_matrix.append(row)
    
    num_patterns = len(patterns)
    num_items = len(items)
    
    # Create Excel file
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # ===== Formats =====
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        })
        number_format = workbook.add_format({
            'border': 1, 'align': 'center', 'num_format': '#,##0'
        })
        input_format = workbook.add_format({
            'bg_color': '#FFFACD', 'border': 1, 'align': 'center', 'num_format': '#,##0'
        })
        formula_format = workbook.add_format({
            'border': 1, 'align': 'center', 'num_format': '#,##0', 'bg_color': '#E2EFDA'
        })
        
        # ===== SHEET 1: Kết quả tối ưu (đặt trước để tham chiếu) =====
        ws_pattern = workbook.add_worksheet('Pattern')
        
        # Title row
        ws_pattern.merge_range('A1:F1', 'KẾT QUẢ TỐI ƯU - Nhập số lượng cây đã cắt vào cột "SL đã cắt" (vàng)', title_format)
        
        # Headers at row 2 (0-indexed row 1)
        pattern_headers = ["STT", "Pattern", "Chiều dài SD", "Phế liệu", "SL tối ưu", "SL đã cắt"]
        for col, header in enumerate(pattern_headers):
            ws_pattern.write(1, col, header, header_format)
        
        # Data starts at row 3 (0-indexed row 2)
        for row_idx, pat in enumerate(patterns):
            data_row = row_idx + 2  # 0-indexed
            ws_pattern.write(data_row, 0, pat.idx, number_format)
            ws_pattern.write(data_row, 1, pat.segments_summary)
            ws_pattern.write(data_row, 2, pat.used_length, number_format)
            ws_pattern.write(data_row, 3, pat.waste, number_format)
            ws_pattern.write(data_row, 4, pat.qty, number_format)
            ws_pattern.write(data_row, 5, 0, input_format)  # User input column
        
        # Column widths
        ws_pattern.set_column('A:A', 6)
        ws_pattern.set_column('B:B', 80)
        ws_pattern.set_column('C:C', 12)
        ws_pattern.set_column('D:D', 10)
        ws_pattern.set_column('E:E', 10)
        ws_pattern.set_column('F:F', 12)
        
        # ===== SHEET 2: Chi tiết cắt =====
        ws_detail = workbook.add_worksheet('Chi tiet cat')
        
        # Title row
        ws_detail.merge_range('A1:G1', f'CHI TIẾT CẮT - {co.name} - {co.steel_profile}', title_format)
        
        # Headers at row 2
        detail_headers = ["No.", "Mã mảnh", "Tên mảnh", "Tên đoạn", "Chiều dài", "SL yêu cầu", "SL đã cắt"]
        for col, header in enumerate(detail_headers):
            ws_detail.write(1, col, header, header_format)
        
        # Add hidden coefficient columns (starting from column H = index 7)
        coef_start_col = 7
        for j in range(num_patterns):
            col_idx = coef_start_col + j
            ws_detail.write(1, col_idx, f"P{j+1}", header_format)
        
        # Data starts at row 3 (0-indexed row 2)
        # Pattern input range in Sheet1: F3:F{2+num_patterns} in 1-indexed = F3:F{num_patterns+2}
        pattern_input_start = 3  # 1-indexed row
        pattern_input_end = 2 + num_patterns  # 1-indexed row
        
        for row_idx, item in enumerate(items):
            data_row = row_idx + 2  # 0-indexed
            excel_row = row_idx + 3  # 1-indexed for formulas
            
            # Main data columns
            ws_detail.write(data_row, 0, row_idx + 1, number_format)
            ws_detail.write(data_row, 1, item.piece_code)
            ws_detail.write(data_row, 2, item.piece_name)
            ws_detail.write(data_row, 3, item.segment_name)
            ws_detail.write(data_row, 4, item.length_mm, number_format)
            ws_detail.write(data_row, 5, item.qty, number_format)
            
            # Write coefficient values in hidden columns (H, I, J, K, ...)
            for j in range(num_patterns):
                col_idx = coef_start_col + j
                ws_detail.write(data_row, col_idx, count_matrix[row_idx][j], number_format)
            
            # Build SUMPRODUCT formula
            # Coefficients: H{row}:{last_col}{row}
            # Pattern inputs: Pattern!$F$3:$F${end}
            first_coef_col = get_column_letter(coef_start_col)  # H
            last_coef_col = get_column_letter(coef_start_col + num_patterns - 1)  # K for 4 patterns
            
            formula = f"=SUMPRODUCT({first_coef_col}{excel_row}:{last_coef_col}{excel_row},Pattern!$F${pattern_input_start}:$F${pattern_input_end})"
            ws_detail.write_formula(data_row, 6, formula, formula_format)
        
        # Column widths
        ws_detail.set_column('A:A', 6)
        ws_detail.set_column('B:B', 14)
        ws_detail.set_column('C:C', 16)
        ws_detail.set_column('D:D', 26)
        ws_detail.set_column('E:E', 10)
        ws_detail.set_column('F:F', 12)
        ws_detail.set_column('G:G', 12)
        
        # Hide coefficient columns
        for j in range(num_patterns):
            col_letter = get_column_letter(coef_start_col + j)
            ws_detail.set_column(f'{col_letter}:{col_letter}', None, None, {'hidden': True})
    
    # Save file
    output.seek(0)
    import time
    timestamp = int(time.time())
    file_name = f"{cutting_order_name}_tracking_{timestamp}.xlsx"
    file_path = f"/files/{file_name}"
    
    # Save to Frappe files
    site_path = frappe.get_site_path()
    full_path = f"{site_path}/public/files/{file_name}"
    
    with open(full_path, 'wb') as f:
        f.write(output.getvalue())
    
    return {
        "success": True,
        "file_url": file_path,
        "file_name": file_name,
        "message": f"Excel file created with {num_items} items and {num_patterns} patterns"
    }
