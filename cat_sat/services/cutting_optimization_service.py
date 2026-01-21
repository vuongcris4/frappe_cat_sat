"""
Cutting Optimization Service for IEA Steel Cutting
Based on Django cat_sat_iea implementation

Phase 1: Find all valid cutting patterns using CP-SAT enumerate_all_solutions
Phase 2: Optimize pattern distribution with multi-objective (waste → surplus → priority)
"""

import frappe
from frappe.utils import flt, cint
from collections import defaultdict
import hashlib
import os
import pickle

try:
    from ortools.sat.python import cp_model
    
    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        """Callback to collect all valid cutting patterns"""
        
        def __init__(self, variables, limit=100000):
            super().__init__()
            self._variables = variables
            self._limit = limit
            self._solutions = []
            self._seen = set()
        
        def on_solution_callback(self):
            if len(self._solutions) >= self._limit:
                self.StopSearch()
                return
            
            # Extract solution
            solution = tuple(self.Value(v) for v in self._variables)
            
            # Skip duplicates
            if solution in self._seen:
                return
            
            self._seen.add(solution)
            self._solutions.append(list(solution))
        
        @property
        def solutions(self):
            return self._solutions
except ImportError:
    cp_model = None
    SolutionCollector = None

# Scaling factor for decimal lengths (1162.2mm -> 11622)
SCALING_FACTOR = 10

# Maximum patterns to generate/cache
SOLUTION_LIMIT = 100000


def get_cache_path(stock_length, piece_lengths, blade_width, max_waste_pct, trim):
    """Generate cache file path based on input parameters"""
    cache_folder = os.path.join(frappe.get_site_path(), "private", "cutting_patterns_cache")
    os.makedirs(cache_folder, exist_ok=True)
    
    params_string = f"{stock_length}-{tuple(sorted(piece_lengths))}-{blade_width}-{max_waste_pct}-{trim}"
    input_hash = hashlib.sha256(params_string.encode('utf-8')).hexdigest()[:16]
    
    return os.path.join(cache_folder, f"patterns_{input_hash}.pkl")


def find_efficient_cutting_patterns(stock_length, piece_lengths, blade_width, max_waste_pct, trim):
    """
    Phase 1: Find all valid cutting patterns using CP-SAT
    
    Args:
        stock_length: Raw stock length (mm)
        piece_lengths: List of segment lengths (mm)
        blade_width: Kerf width (mm)
        max_waste_pct: Maximum waste percentage (0.01 = 1%)
        trim: Trim cut at start (mm)
    
    Returns:
        List of (obj_value, solution) tuples where:
        - obj_value: Total material used (mm)
        - solution: List of counts for each piece length
    """
    # Convert to integers for CP-SAT
    stock_int = int(stock_length * SCALING_FACTOR)
    pieces_int = [int(l * SCALING_FACTOR) for l in piece_lengths]
    blade_int = int(blade_width * SCALING_FACTOR)
    trim_int = int(trim * SCALING_FACTOR)
    
    model = cp_model.CpModel()
    num_pieces = len(pieces_int)
    
    # Calculate max pieces that could fit for each length
    # For short segments (like 40mm), we need many more pieces per bar
    min_piece_len = min(pieces_int) if pieces_int else 1000
    max_possible_pieces = max(150, stock_int // min_piece_len + 1)
    
    # Variables: count of each segment type in a single pattern
    counts = [model.NewIntVar(0, max_possible_pieces, f'segment_{i}') for i in range(num_pieces)]
    
    # Total material used = sum(length * count) + sum(count) * blade + trim
    total_pieces_length = sum(counts[i] * pieces_int[i] for i in range(num_pieces))
    total_kerf = cp_model.LinearExpr.Sum(counts) * blade_int
    total_used = total_pieces_length + total_kerf + trim_int
    
    # Constraint: Must fit in stock
    model.Add(total_used <= stock_int)
    
    # Constraint: Adaptive minimum utilization based on segment lengths
    # For short segments (< 500mm), allow more waste since bundling many is harder
    # For longer segments, require higher utilization
    avg_piece_len = sum(pieces_int) / len(pieces_int) if pieces_int else 1000
    if avg_piece_len < 500 * SCALING_FACTOR:  # Short segments
        adaptive_waste_pct = 0.10  # Allow up to 10% waste for short segments
    elif avg_piece_len < 1000 * SCALING_FACTOR:  # Medium segments
        adaptive_waste_pct = 0.05  # Allow 5% waste
    else:
        adaptive_waste_pct = max_waste_pct  # Use default 1.5%
    
    min_used = int(stock_int * (1 - adaptive_waste_pct))
    model.Add(total_used >= min_used)
    
    # Constraint: Waste >= 0 (implicit from above, but explicit for clarity)
    waste_var = model.NewIntVar(0, stock_int, 'waste')
    model.Add(waste_var == stock_int - total_used)
    model.Add(waste_var >= 0)
    
    # Setup solver to enumerate all solutions
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.log_search_progress = False
    solver.parameters.num_search_workers = 1
    
    collector = SolutionCollector(counts, SOLUTION_LIMIT)
    solver.Solve(model, collector)
    
    if not collector.solutions:
        return []
    
    # Calculate obj_value (material used) for each solution
    results = []
    for sol in collector.solutions:
        # Calculate total used in original scale
        used_int = sum(sol[i] * pieces_int[i] for i in range(num_pieces))
        used_int += sum(sol) * blade_int + trim_int
        obj_value = used_int / SCALING_FACTOR
        results.append((obj_value, sol))
    
    # Sort by obj_value descending (higher usage = less waste = better)
    results.sort(key=lambda x: x[0], reverse=True)
    
    return results


def get_or_calculate_patterns(stock_length, piece_lengths, blade_width, max_waste_pct=0.015, trim=0):
    """
    Get patterns from cache or calculate new ones
    
    Returns:
        List of (obj_value, solution) tuples
    """
    cache_path = get_cache_path(stock_length, piece_lengths, blade_width, max_waste_pct, trim)
    
    # Try to load from cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                patterns = pickle.load(f)
            
            # Filter patterns that still fit after trim
            valid_patterns = [
                (obj, sol) for obj, sol in patterns
                if obj <= stock_length + 0.001
            ]
            
            if valid_patterns:
                return valid_patterns
        except Exception:
            pass  # Cache corrupted, recalculate
    
    # Calculate new patterns
    patterns = find_efficient_cutting_patterns(
        stock_length, piece_lengths, blade_width, max_waste_pct, trim
    )
    
    # Save to cache
    if patterns:
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(patterns, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass  # Cache write failed, continue anyway
    
    return patterns


@frappe.whitelist()
def run_optimization(order_name: str):
    """Main entry point for cutting optimization"""
    if not cp_model:
        frappe.throw("Thư viện 'ortools' chưa được cài đặt. Vui lòng cài đặt: 'pip install ortools'")
    
    order = frappe.get_doc("Cutting Order", order_name)
    
    if order.docstatus == 1:
        frappe.throw("Không thể tối ưu hóa Lệnh cắt đã Submit. Vui lòng Cancel và Amend để chỉnh sửa.")
    
    if not order.items:
        frappe.throw("Lệnh cắt chưa có chi tiết nào.")
    
    # Load Cutting Settings
    settings = frappe.get_single("Cutting Settings")
    
    # Prepare input
    stock_length = flt(order.stock_length)
    blade_width = flt(order.blade_width or 1)
    
    # Determine trim based on mode (MCTĐ vs Laser) from settings
    if order.enable_bundling:
        # MCTĐ mode
        default_trim = flt(settings.mctd_trim_cut or 15)
        max_segments = cint(settings.mctd_max_segments_per_pattern or 5)
    else:
        # Laser mode
        default_trim = flt(settings.laser_trim_cut or 10)
        max_segments = 0  # No limit for laser
    
    # Use order.trim_cut if set, otherwise use settings default
    trim = flt(order.trim_cut) if order.trim_cut else default_trim
    
    if stock_length <= 0:
        frappe.throw("Chiều dài cây sắt phải lớn hơn 0")
    
    effective_length = stock_length - trim
    if effective_length <= 0:
        frappe.throw("Chiều dài khả dụng không đủ (Chiều dài - Tề đầu <= 0)")
    
    # Build demand map and segment info (preserving ALL metadata for traceability)
    item_map = defaultdict(int)
    piece_names = {}  # length -> name
    segment_info = {}  # length -> full metadata dict
    
    # Get source info from Cutting Specification if available
    source_spec_name = order.cutting_specification or ""
    source_item = ""
    spec_details_by_length = {}  # Lookup by length only
    
    if source_spec_name:
        try:
            spec = frappe.get_doc("Cutting Specification", source_spec_name)
            source_item = frappe.db.get_value("Item", {"cutting_specification": source_spec_name}, "name") or ""
            
            # Cache for Item piece_name lookup
            piece_name_cache = {}
            
            # Build a lookup from spec.details by length for full metadata
            # Track unique piece info per length
            piece_codes_by_length = defaultdict(set)  # Track unique bom_items per length
            
            for detail in spec.details:
                length = flt(detail.length_mm)
                bom_item = detail.bom_item or ""
                
                # Get piece_name from Item's custom field (with cache)
                if bom_item and bom_item not in piece_name_cache:
                    item_piece_name = frappe.db.get_value("Item", bom_item, "piece_name")
                    # Just use the short name (e.g., "Khung tựa đôi")
                    piece_name_cache[bom_item] = item_piece_name or bom_item
                
                # Collect bom_items for this length
                if bom_item:
                    piece_codes_by_length[length].add(piece_name_cache.get(bom_item, bom_item))
                
                # Store metadata by length - if multiple segments have same length, merge info
                if length not in spec_details_by_length:
                    spec_details_by_length[length] = {
                        "piece_name": piece_name_cache.get(bom_item, bom_item) if bom_item else "",
                        "piece_code": bom_item,
                        "steel_profile": detail.steel_profile or "",
                        "segment_name": detail.segment_name or f"{length}mm",
                        "length_mm": length,
                        "qty_segment_per_piece": cint(detail.qty_per_unit or 1),
                        "punch_holes": cint(detail.punch_hole_qty or 0),
                        "rivet_holes": cint(detail.rivet_hole_qty or 0),
                        "drill_holes": cint(detail.drill_hole_qty or 0),
                        "bending": detail.bend_type or "",
                        "note": detail.note or "",
                        "source_spec": source_spec_name,
                        "source_item": source_item
                    }
            
            # Update piece_name to include all pieces for this length
            for length, names in piece_codes_by_length.items():
                if length in spec_details_by_length:
                    spec_details_by_length[length]["piece_name"] = ", ".join(sorted(names))
                    
        except Exception as e:
            frappe.log_error(f"Error loading spec {source_spec_name}: {e}", "Cutting Optimization")
    
    for item in order.items:
        length = flt(item.length_mm)
        # NEW: Track machine type per segment
        machine_type = getattr(item, 'cut_by', '') or 'Laser'
        item_map[length] += cint(item.qty)
        
        if length not in piece_names:
            segment_name = item.segment_name or f"{length}mm"
            piece_names[length] = segment_name
            
            # Get metadata from spec if available, otherwise from order.items
            if length in spec_details_by_length:
                segment_info[length] = spec_details_by_length[length].copy()
            else:
                # Fallback to data from order.items - use piece_name and piece_code from order
                segment_info[length] = {
                    "piece_code": getattr(item, 'piece_code', '') or '',
                    "piece_name": getattr(item, 'piece_name', '') or '',
                    "steel_profile": order.steel_profile or "",
                    "segment_name": segment_name,
                    "length_mm": length,
                    "punch_holes": cint(getattr(item, 'punch_holes', 0)),
                    "rivet_holes": cint(getattr(item, 'rivet_holes', 0)),
                    "drill_holes": cint(getattr(item, 'drill_holes', 0)),
                    "bending": getattr(item, 'bending', '') or '',
                    "note": getattr(item, 'note', '') or '',
                    "source_spec": source_spec_name,
                    "source_item": source_item
                }
            # Store machine type for this length
            segment_info[length]["cut_by"] = machine_type

    
    piece_lengths = sorted(item_map.keys(), reverse=True)
    demands = [item_map[l] for l in piece_lengths]
    
    # Validate
    for l in piece_lengths:
        if l > effective_length:
            frappe.throw(f"Chi tiết dài {l}mm lớn hơn chiều dài khả dụng ({effective_length}mm)")
    
    # NEW: Split segments by machine type (cut_by field)
    laser_segments = {}  # length -> qty
    mctd_segments = {}   # length -> qty
    
    for item in order.items:
        length = flt(item.length_mm)
        qty = cint(item.qty)
        machine = getattr(item, 'cut_by', '') or 'Laser'
        
        if machine == 'MCTĐ':
            mctd_segments[length] = mctd_segments.get(length, 0) + qty
        else:
            laser_segments[length] = laser_segments.get(length, 0) + qty
    
    # Run separate optimizations
    sol = []
    
    # Laser optimization (blade_width = 1mm fixed for Laser)
    if laser_segments:
        laser_lengths = sorted(laser_segments.keys(), reverse=True)
        laser_demands = [laser_segments[l] for l in laser_lengths]
        laser_blade = 1.0  # Fixed for Laser
        
        laser_sol = solve_laser_cutting_stock(
            laser_lengths,
            laser_demands,
            piece_names,
            stock_length,
            laser_blade,
            trim,
            cint(order.max_over_production or 10)
        )
        # Mark patterns as Laser-cut
        for pat in laser_sol:
            pat['machine'] = 'Laser'
        sol.extend(laser_sol)
    
    # MCTĐ optimization (use mctd_blade_width from order)
    if mctd_segments:
        if not order.steel_profile:
            frappe.throw("Vui lòng chọn Steel Profile khi có segment MCTĐ.")
        
        mctd_lengths = sorted(mctd_segments.keys(), reverse=True)
        mctd_demands = [mctd_segments[l] for l in mctd_lengths]
        mctd_blade = flt(order.mctd_blade_width or 2.5)  # From order settings
        
        bundle_factors_str = frappe.db.get_value("Steel Profile", order.steel_profile, "bundle_factors")
        if not bundle_factors_str:
            bundle_factors_str = "14 16 18 20"  # Default factors
        
        factors = [1]  # Always include manual cut
        import re
        factor_strs = [s.strip() for s in re.split(r'[,\s.;]+', bundle_factors_str) if s.strip()]
        for f in factor_strs:
            try:
                factor = int(f)
                if factor > 1 and factor not in factors:
                    factors.append(factor)
            except ValueError:
                pass
        factors = sorted(set(factors), reverse=True)
        
        mctd_sol = solve_bundled_cutting_stock(
            mctd_lengths,
            mctd_demands,
            piece_names,
            stock_length,
            mctd_blade,
            trim,
            factors,
            cint(order.manual_cut_limit or 10),
            cint(order.max_over_production or 20),
            max_segments
        )
        # Mark patterns as MCTĐ-cut
        for pat in mctd_sol:
            pat['machine'] = 'MCTĐ'
        sol.extend(mctd_sol)
    
    # Save results with segment details
    order.set("optimization_result", [])
    patterns_with_segments = []  # Store segments data for each pattern
    
    for pat in sol:
        # Build pattern string with piece names and machining details
        pattern_parts = []
        segments_data = []
        
        for length, count in pat['pattern'].items():
            # Get segment info for display
            info = segment_info.get(length, {})
            segment_name = info.get("segment_name", "") or f"{length}mm"
            piece_name = info.get("piece_name", "")
            piece_code = info.get("piece_code", "") or info.get("source_item", "")
            
            # Build machining details for pattern display
            machining_parts = []
            if info.get("punch_holes", 0) > 0:
                machining_parts.append(f"{info['punch_holes']} dập")
            if info.get("rivet_holes", 0) > 0:
                machining_parts.append(f"{info['rivet_holes']} tán")
            if info.get("drill_holes", 0) > 0:
                machining_parts.append(f"{info['drill_holes']} khoan")
            if info.get("bending", "") and info.get("bending", "") != "Không":
                machining_parts.append(info["bending"])
            
            # Format: "3x Tên đoạn 497mm [Mảnh: Tên mảnh]" 
            # Example: "3x H10-20 (uốn) 497mm [Khung tựa]"
            length_str = f"{int(length)}" if length == int(length) else f"{length:.1f}"
            
            # Build segment display name
            display_name = segment_name
            if machining_parts:
                machining_str = ", ".join(machining_parts)
                display_name = f"{segment_name} ({machining_str})"
            
            # Build piece info bracket
            if piece_name:
                piece_info = f" [{piece_name}]"
            else:
                piece_info = ""
            
            pattern_parts.append(f"{count}x {display_name} {length_str}mm{piece_info}")
            
            # Build segment child data with FULL traceability
            segments_data.append({
                "piece_code": info.get("piece_code", ""),
                "piece_name": info.get("piece_name", ""),
                "segment_name": info.get("segment_name", f"{length}mm"),
                "steel_profile": info.get("steel_profile", ""),
                "length_mm": length,
                "quantity": count,
                "punch_holes": info.get("punch_holes", 0),
                "rivet_holes": info.get("rivet_holes", 0),
                "drill_holes": info.get("drill_holes", 0),
                "bending": info.get("bending", ""),
                "note": info.get("note", ""),
                "source_spec": info.get("source_spec", ""),
                "source_item": info.get("source_item", "")
            })
        
        pattern_str = " + ".join(pattern_parts)
        
        # Calculate waste including trim
        # used_length is the actual material used for cuts + kerf
        # waste = stock_length - used_length (this already represents unused portion)
        # The waste should be at minimum the trim cut value
        used_len = flt(pat.get('used_length', 0))
        raw_waste = stock_length - used_len
        # Waste must be at least the trim cut amount
        actual_waste = max(raw_waste, trim)
        
        # Build segments summary for grid display
        # Format: "3x Tên đoạn (machining) 497mm [Tên mảnh]"
        segments_summary_parts = []
        for seg in segments_data:
            segment_name = seg.get("segment_name", "") or f"{seg.get('length_mm', 0)}mm"
            piece_name = seg.get("piece_name", "")
            length = seg.get("length_mm", 0)
            qty = seg.get("quantity", 0)
            
            if qty > 0:
                # Build machining details list
                machining_parts = []
                if seg.get("punch_holes", 0) > 0:
                    machining_parts.append(f"{seg['punch_holes']} dập")
                if seg.get("rivet_holes", 0) > 0:
                    machining_parts.append(f"{seg['rivet_holes']} tán")
                if seg.get("drill_holes", 0) > 0:
                    machining_parts.append(f"{seg['drill_holes']} khoan")
                if seg.get("bending", "") and seg.get("bending", "") != "Không":
                    machining_parts.append(seg["bending"])
                
                # Format: "3x Tên đoạn (machining) 497mm [Tên mảnh]"
                length_str = f"{int(length)}" if length == int(length) else f"{length:.1f}"
                
                # Build segment display name
                display_name = segment_name
                if machining_parts:
                    machining_str = ", ".join(machining_parts)
                    display_name = f"{segment_name} ({machining_str})"
                
                # Build piece info bracket
                if piece_name:
                    piece_info = f" [{piece_name}]"
                else:
                    piece_info = ""
                
                summary_part = f"{qty}x {display_name} {length_str}mm{piece_info}"
                    
                segments_summary_parts.append(summary_part)
        segments_summary = ", ".join(segments_summary_parts)
        
        pattern_row = order.append("optimization_result", {
            "machine": pat.get('machine', 'Laser'),
            "pattern": pattern_str,
            "segments_summary": segments_summary,
            "used_length": used_len,
            "waste": actual_waste,
            "qty": pat['qty']
        })
        
        # Store segments data for this pattern row
        patterns_with_segments.append((pattern_row, segments_data))
    
    # Save order first to get pattern row names
    order.status = "Optimized"
    order.save(ignore_permissions=True)
    
    # Now add segments to each pattern row using direct insert
    for pattern_row, segments_data in patterns_with_segments:
        if pattern_row.name and segments_data:
            for idx, seg in enumerate(segments_data, 1):
                seg_doc = frappe.new_doc("Pattern Segment")
                seg_doc.parent = pattern_row.name
                seg_doc.parenttype = "Cutting Pattern"
                seg_doc.parentfield = "segments"
                seg_doc.idx = idx
                seg_doc.piece_code = seg.get("piece_code", "")
                seg_doc.piece_name = seg.get("piece_name", "")
                seg_doc.segment_name = seg.get("segment_name", "")
                seg_doc.steel_profile = seg.get("steel_profile", "")
                seg_doc.length_mm = seg.get("length_mm", 0)
                seg_doc.quantity = seg.get("quantity", 0)
                seg_doc.punch_holes = seg.get("punch_holes", 0)
                seg_doc.rivet_holes = seg.get("rivet_holes", 0)
                seg_doc.drill_holes = seg.get("drill_holes", 0)
                seg_doc.bending = seg.get("bending", "")
                seg_doc.note = seg.get("note", "")
                seg_doc.source_spec = seg.get("source_spec", "")
                seg_doc.source_item = seg.get("source_item", "")
                seg_doc.db_insert()
    
    # Generate HTML result display
    result_html = generate_result_html(
        sol, piece_lengths, piece_names, demands, stock_length, order.enable_bundling
    )
    order.result_html = result_html
    order.save(ignore_permissions=True)
    
    return sol


def generate_result_html(patterns, piece_lengths, piece_names, demands, stock_length, is_bundling=False):
    """
    Generate HTML display for optimization results
    
    For MCTD (bundling mode): Django app style with waste rows and bundle factor columns
    For Laser: Simple pattern table
    """
    from datetime import datetime
    
    if not patterns:
        return "<p>Không có kết quả tối ưu.</p>"
    
    html_parts = []
    
    # Header with timestamp
    now = datetime.now()
    html_parts.append(f"<p><b>Thời gian:</b> {now.strftime('%d/%m/%Y %H:%M:%S')}</p>")
    html_parts.append(f"<p><b>Chiều dài cây sắt:</b> {stock_length}mm</p>")
    
    # Calculate production totals
    production = {l: 0 for l in piece_lengths}
    for pat in patterns:
        for l, c in pat['pattern'].items():
            production[l] += c * pat['qty']
    
    # Summary table
    title = "TỔNG KẾT CẮT TỰ ĐỘNG" if is_bundling else "TỔNG KẾT CẮT LASER"
    html_parts.append(f"<h4>{title}</h4>")
    html_parts.append('<table class="table table-bordered table-sm" style="text-align:center">')
    html_parts.append('<thead><tr><th>Tên sắt</th><th>Đoạn (mm)</th><th>SL cần (đoạn)</th><th>SL cắt (đoạn)</th><th>Tồn kho (đoạn)</th></tr></thead>')
    html_parts.append('<tbody>')
    
    for i, l in enumerate(piece_lengths):
        name = piece_names.get(l, f"{l}mm")
        demand = demands[i]
        produced = production.get(l, 0)
        surplus = produced - demand
        l_str = f"{int(l)}" if l == int(l) else f"{l:.1f}"
        html_parts.append(f'<tr><td>{name}</td><td>{l_str}</td><td>{demand}</td><td>{produced}</td><td>{surplus}</td></tr>')
    
    html_parts.append('</tbody></table>')
    
    # Total stats
    total_bars = sum(pat['qty'] for pat in patterns)
    total_waste = sum(pat.get('waste', 0) * pat['qty'] for pat in patterns)
    waste_pct = (total_waste / (stock_length * total_bars) * 100) if total_bars > 0 else 0
    
    # Count by type
    if is_bundling:
        machine_bars = sum(pat['qty'] for pat in patterns if pat.get('factor', 1) > 1)
        manual_bars = total_bars - machine_bars
        html_parts.append('<hr>')
        html_parts.append(f"<p><b>Tổng số cây sắt cần dùng:</b> {total_bars} cây</p>")
        html_parts.append(f"<p><b>Cắt máy:</b> {machine_bars} cây, <b>Cắt tay:</b> {manual_bars} cây</p>")
        html_parts.append(f"<p><b>Tổng hao hụt dài:</b> {total_waste/1000:.2f}m</p>")
        html_parts.append(f"<p><b>Hao hụt:</b> {waste_pct:.2f}%</p>")
    else:
        html_parts.append('<hr>')
        html_parts.append(f"<p><b>Tổng số cây sắt cần dùng:</b> {total_bars} cây</p>")
        html_parts.append(f"<p><b>Tổng hao hụt dài:</b> {total_waste/1000:.2f}m</p>")
        html_parts.append(f"<p><b>Hao hụt:</b> {waste_pct:.2f}%</p>")
    
    # Detailed cutting plan table
    html_parts.append(f"<h4>KẾ HOẠCH CẮT CHI TIẾT ({len(patterns)} loại)</h4>")
    
    if is_bundling:
        # MCTD format: rows by waste, columns by lengths + bundle factors
        # Get unique bundle factors
        factors = sorted(set(pat.get('factor', 1) for pat in patterns), reverse=True)
        
        # Build header: STT | Hao hụt | lengths... | factor columns... | Tổng cây
        html_parts.append('<table class="table table-bordered table-sm" style="text-align:center; font-size:0.9em">')
        html_parts.append('<thead><tr><th>STT</th><th>Hao hụt (mm)</th>')
        
        for l in piece_lengths:
            l_str = f"{int(l)}" if l == int(l) else f"{l:.1f}"
            html_parts.append(f'<th>{l_str}</th>')
        
        for f in factors:
            html_parts.append(f'<th>{f}<br>cây/bó</th>')
        
        html_parts.append('<th>Tổng cây</th></tr></thead>')
        html_parts.append('<tbody>')
        
        for idx, pat in enumerate(patterns, 1):
            waste = pat.get('waste', 0)
            waste_str = f"{int(waste)}" if waste == int(waste) else f"{waste:.1f}"
            factor = pat.get('factor', 1)
            qty = pat['qty']
            
            html_parts.append(f'<tr><td>{idx}</td><td>{waste_str}</td>')
            
            # Segment counts
            for l in piece_lengths:
                count = pat['pattern'].get(l, 0)
                if count > 0:
                    html_parts.append(f'<td style="font-weight:bold">{count}</td>')
                else:
                    html_parts.append('<td></td>')
            
            # Bundle factor columns - put qty in the right factor column
            for f in factors:
                if factor == f and qty > 0:
                    html_parts.append(f'<td style="font-weight:bold">{qty}</td>')
                else:
                    html_parts.append('<td></td>')
            
            html_parts.append(f'<td style="font-weight:bold">{qty}</td>')
            html_parts.append('</tr>')
        
        html_parts.append('</tbody></table>')
    else:
        # Laser format: simple pattern table
        html_parts.append('<table class="table table-bordered table-sm" style="text-align:center; font-size:0.9em">')
        html_parts.append('<thead><tr><th>STT</th>')
        
        for l in piece_lengths:
            name = piece_names.get(l, "")
            l_str = f"{int(l)}" if l == int(l) else f"{l:.1f}"
            html_parts.append(f'<th style="min-width:60px">{name}<br>({l_str}mm)</th>')
        
        html_parts.append('<th>Hao hụt (mm)</th><th>SL cây sắt</th></tr></thead>')
        html_parts.append('<tbody>')
        
        for idx, pat in enumerate(patterns, 1):
            html_parts.append(f'<tr><td>{idx}</td>')
            
            for l in piece_lengths:
                count = pat['pattern'].get(l, 0)
                if count > 0:
                    html_parts.append(f'<td style="font-weight:bold">{count}</td>')
                else:
                    html_parts.append('<td></td>')
            
            waste = pat.get('waste', 0)
            waste_str = f"{int(waste)}" if waste == int(waste) else f"{waste:.1f}"
            html_parts.append(f'<td>{waste_str}</td>')
            html_parts.append(f'<td style="font-weight:bold">{pat["qty"]}</td>')
            html_parts.append('</tr>')
        
        html_parts.append('</tbody></table>')
    
    return '\n'.join(html_parts)


def solve_laser_cutting_stock(piece_lengths, demands, piece_names, stock_length, blade_width, trim, max_surplus):
    """
    Laser cutting optimization with multi-objective:
    1. Minimize total waste
    2. Minimize total surplus
    
    Returns:
        List of pattern dicts with 'pattern', 'qty', 'waste', 'used_length'
    """
    # Phase 1: Get patterns
    patterns = get_or_calculate_patterns(stock_length, piece_lengths, blade_width, 0.015, trim)
    
    if not patterns:
        frappe.throw("Không tìm được pattern nào phù hợp.")
    
    num_patterns = len(patterns)
    num_pieces = len(piece_lengths)
    
    # Phase 2: Optimize distribution
    model = cp_model.CpModel()
    
    # Variables: number of times to use each pattern
    x = [model.NewIntVar(0, sum(demands) * 2, f'x_{j}') for j in range(num_patterns)]
    
    # Production for each piece type
    production = []
    surplus_vars = []
    
    # Calculate max pieces per pattern (for adaptive surplus)
    max_pieces_per_pattern = max(sum(sol) for _, sol in patterns) if patterns else 1
    
    for i in range(num_pieces):
        # Production = sum(pattern_count[i] * x[j]) for all patterns j
        prod = sum(patterns[j][1][i] * x[j] for j in range(num_patterns))
        production.append(prod)
        
        # Surplus variable - adaptive limit based on pattern capacity
        # For high-density patterns (many pieces per bar), allow more surplus
        # since one bar can produce way more than demand
        adaptive_surplus = max(max_surplus, max_pieces_per_pattern * 2)
        
        s = model.NewIntVar(0, sum(demands), f'surplus_{i}')
        model.Add(s == prod - demands[i])
        model.Add(prod >= demands[i])  # Must meet demand
        model.Add(s <= adaptive_surplus)  # Adaptive surplus limit
        surplus_vars.append(s)
    
    # Calculate waste for each pattern (in mm, scaled)
    waste_per_pattern = []
    for obj_value, sol in patterns:
        waste = stock_length - obj_value
        waste_per_pattern.append(int(waste * SCALING_FACTOR))
    
    # Objective 1: Minimize total waste
    total_waste = sum(waste_per_pattern[j] * x[j] for j in range(num_patterns))
    model.Minimize(total_waste)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        frappe.throw("Không tìm được phương án cắt. Thử tăng tồn kho cho phép.")
    
    min_waste = int(solver.ObjectiveValue())
    
    # Lock waste and minimize surplus
    model.Add(total_waste == min_waste)
    total_surplus = sum(surplus_vars)
    model.Minimize(total_surplus)
    
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        frappe.throw("Không tìm được phương án tối ưu tồn kho.")
    
    # Extract solution
    result_patterns = []
    for j in range(num_patterns):
        qty = solver.Value(x[j])
        if qty > 0:
            obj_value, sol = patterns[j]
            pattern_dict = {piece_lengths[i]: sol[i] for i in range(num_pieces) if sol[i] > 0}
            
            # obj_value includes trim, so subtract trim to get pure cuts+kerf
            # used_length = cuts + kerf only (not including trim)
            used_length = obj_value - trim
            
            result_patterns.append({
                'pattern': pattern_dict,
                'qty': qty,
                'used_length': used_length,
                'waste': stock_length - used_length  # This naturally includes trim
            })
    
    return result_patterns


def solve_bundled_cutting_stock(piece_lengths, demands, piece_names, stock_length, blade_width, trim, 
                                 factors, manual_cut_limit, max_over, max_segments_per_pattern=5):
    """
    MCTĐ (Bundle cutting) optimization
    
    Phase 1: Generate patterns (max N different sizes from settings)
    Phase 2: Optimize bundle distribution with factors
    """
    # Phase 1: Get patterns
    patterns = get_or_calculate_patterns(stock_length, piece_lengths, blade_width, 0.015, trim)
    
    if not patterns:
        frappe.throw("Không tìm được pattern nào phù hợp.")
    
    # Filter to max N different sizes per pattern (MCTĐ machine constraint from settings)
    max_segs = max_segments_per_pattern if max_segments_per_pattern > 0 else 5
    if len(piece_lengths) > max_segs:
        filtered = [
            (obj, sol) for obj, sol in patterns
            if sum(1 for s in sol if s > 0) <= max_segs
        ]
        if filtered:
            patterns = filtered
    
    num_patterns = len(patterns)
    num_pieces = len(piece_lengths)
    
    # Phase 2: Bundle optimization
    model = cp_model.CpModel()
    
    # Filter out factor 0
    pos_factors = [f for f in factors if f > 0]
    
    # Variables: b[pattern][factor] = number of bundles
    b = {}
    for j in range(num_patterns):
        for f in pos_factors:
            # Upper bound estimation
            max_bundles = max(1, sum(demands) // f + 1)
            b[(j, f)] = model.NewIntVar(0, max_bundles, f'b_{j}_{f}')
    
    # Production for each piece type
    production = []
    for i in range(num_pieces):
        terms = []
        for j in range(num_patterns):
            count_in_pattern = patterns[j][1][i]
            if count_in_pattern > 0:
                for f in pos_factors:
                    terms.append(count_in_pattern * f * b[(j, f)])
        
        if terms:
            prod = sum(terms)
        else:
            prod = 0
        production.append(prod)
    
    # Constraints
    surplus_vars = []
    max_factor = max(pos_factors) if pos_factors else 1
    for i in range(num_pieces):
        if isinstance(production[i], int):
            if production[i] < demands[i]:
                frappe.throw(f"Không thể đáp ứng nhu cầu cho đoạn {piece_lengths[i]}mm")
        else:
            model.Add(production[i] >= demands[i])
            # Relax constraint: allow more over-production with large bundle factors
            # Each piece can have up to (max_over * max_factor) extra
            max_surplus = max(max_over * max_factor, demands[i])
            model.Add(production[i] <= demands[i] + max_surplus)
            
            s = model.NewIntVar(0, max_surplus, f'surplus_{i}')
            model.Add(s == production[i] - demands[i])
            surplus_vars.append(s)
    
    # Limit manual cuts (factor = 1)
    if 1 in pos_factors:
        manual_cuts = sum(b[(j, 1)] for j in range(num_patterns))
        model.Add(manual_cuts <= manual_cut_limit)
    
    # Calculate waste per pattern
    waste_per_pattern = []
    for obj_value, sol in patterns:
        waste = stock_length - obj_value
        waste_per_pattern.append(int(waste * 1000))  # Scale for integer math
    
    # Objective: Minimize waste (weighted by total bars used)
    total_waste_terms = []
    total_bars_terms = []
    for j in range(num_patterns):
        for f in pos_factors:
            total_bars_terms.append(f * b[(j, f)])
            total_waste_terms.append(waste_per_pattern[j] * f * b[(j, f)])
    
    # Multi-objective: waste * W1 + bars * W2
    W1 = 1000000
    W2 = 1
    objective = sum(total_waste_terms) * W1 + sum(total_bars_terms) * W2
    model.Minimize(objective)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        frappe.throw("Không tìm được phương án. Thử tăng cắt tay hoặc tồn kho cho phép.")
    
    # Extract solution
    result_patterns = []
    for j in range(num_patterns):
        for f in pos_factors:
            num_bundles = solver.Value(b[(j, f)])
            if num_bundles > 0:
                obj_value, sol = patterns[j]
                pattern_dict = {piece_lengths[i]: sol[i] for i in range(num_pieces) if sol[i] > 0}
                
                # obj_value includes trim, subtract it for pure cuts+kerf
                used_length = obj_value - trim
                
                result_patterns.append({
                    'pattern': pattern_dict,
                    'qty': num_bundles * f,  # Total bars
                    'factor': f,
                    'bundles': num_bundles,
                    'used_length': used_length,
                    'waste': stock_length - used_length  # Includes trim naturally
                })
    
    return result_patterns
