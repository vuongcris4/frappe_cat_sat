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
    """Generate cache file path based on input parameters
    
    CRITICAL: piece_lengths order must be preserved (NOT sorted) because
    pattern solutions are arrays indexed by position. If we sort here but
    use unsorted order when looking up, values will be misaligned.
    """
    cache_folder = os.path.join(frappe.get_site_path(), "private", "cutting_patterns_cache")
    os.makedirs(cache_folder, exist_ok=True)
    
    # MUST use tuple(piece_lengths) NOT sorted - order matters for pattern indexing
    params_string = f"{stock_length}-{tuple(piece_lengths)}-{blade_width}-{max_waste_pct}-{trim}"
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
    try:
        return _run_optimization_impl(order_name)
    except Exception as e:
        import traceback
        error_msg = f"Optimization Error: {str(e)}\n\n{traceback.format_exc()}"
        frappe.log_error(error_msg, "Cutting Optimization Error")
        raise

def _run_optimization_impl(order_name: str):
    """Internal implementation of optimization"""
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
    # CRITICAL: Use (length, segment_name) as key to avoid incorrect aggregation
    # Segments with same length but different machining MUST be separate
    item_map = defaultdict(int)  # segment_key -> qty
    segment_info = {}  # segment_key -> full metadata dict
    piece_lengths = []  # ordered list of lengths (can have duplicates)
    segment_keys = []   # ordered list of segment_keys for pattern mapping
    
    # Get source info from Cutting Specification if available
    source_spec_name = order.cutting_specification or ""
    source_item = ""
    
    if source_spec_name:
        try:
            spec = frappe.get_doc("Cutting Specification", source_spec_name)
            source_item = frappe.db.get_value("Item", {"cutting_specification": source_spec_name}, "name") or ""
        except Exception as e:
            frappe.log_error(f"Error loading spec {source_spec_name}: {e}", "Cutting Optimization")
    
    # Process each item as a unique segment type
    for item in order.items:
        length = flt(item.length_mm)
        qty = cint(item.qty)
        segment_name = item.segment_name or f"{length}mm"
        machine_type = getattr(item, 'cut_by', '') or 'Laser'
        piece_code = getattr(item, 'piece_code', '') or ''
        
        # Create unique segment key: (length, segment_name, piece_code)
        # This ensures:
        # 1. Segments with same length but different machining stay separate
        # 2. Segments belonging to different pieces (PHOI) are tracked separately
        # Each segment belongs to exactly one piece for accurate traceability
        segment_key = (length, segment_name, piece_code)
        
        # Sum quantities for same segment_key (identical length + machining + piece)
        item_map[segment_key] += qty
        
        if segment_key not in segment_info:
            segment_info[segment_key] = {
                "piece_code": piece_code,
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
                "source_item": source_item,
                "cut_by": machine_type
            }
            # Add to ordered lists (first occurrence)
            segment_keys.append(segment_key)
            piece_lengths.append(length)
    
    # Build demands in same order as segment_keys
    demands = [item_map[sk] for sk in segment_keys]
    
    # For pattern name display
    piece_names = {sk: segment_info[sk]["segment_name"] for sk in segment_keys}
    
    # Validate
    for i, length in enumerate(piece_lengths):
        if length > effective_length:
            seg_name = segment_info[segment_keys[i]]["segment_name"]
            frappe.throw(f"Chi tiết '{seg_name}' dài {length}mm lớn hơn chiều dài khả dụng ({effective_length}mm)")
    
    # Split segments by machine type (cut_by field)
    laser_indices = []  # indices into segment_keys for laser cuts
    mctd_indices = []   # indices for MCTĐ cuts
    
    for i, sk in enumerate(segment_keys):
        machine = segment_info[sk].get("cut_by", "Laser")
        if machine == 'MCTĐ':
            mctd_indices.append(i)
        else:
            laser_indices.append(i)
    
    # Build laser-specific data
    laser_lengths = [piece_lengths[i] for i in laser_indices]
    laser_demands = [demands[i] for i in laser_indices]
    laser_keys = [segment_keys[i] for i in laser_indices]
    laser_piece_names = {segment_keys[i]: piece_names[segment_keys[i]] for i in laser_indices}
    
    # Build MCTĐ-specific data  
    mctd_lengths = [piece_lengths[i] for i in mctd_indices]
    mctd_demands = [demands[i] for i in mctd_indices]
    mctd_keys = [segment_keys[i] for i in mctd_indices]
    mctd_piece_names = {segment_keys[i]: piece_names[segment_keys[i]] for i in mctd_indices}    
    # Run separate optimizations
    sol = []
    
    # Laser optimization (blade_width = 1mm fixed for Laser)
    if laser_lengths:
        laser_blade = 1.0  # Fixed for Laser
        
        # Get max_patterns from settings (default 20), 0 = no limit
        laser_max_patterns = cint(settings.laser_max_patterns or 20)
        if laser_max_patterns <= 0:
            laser_max_patterns = 0  # No limit
        
        try:
            laser_sol = solve_laser_cutting_stock(
                laser_lengths,
                laser_demands,
                laser_keys,  # Pass segment_keys for pattern mapping
                laser_piece_names,
                stock_length,
                laser_blade,
                trim,
                cint(order.max_over_production or 50),
                laser_max_patterns
            )
            # Mark patterns as Laser-cut
            for pat in laser_sol:
                pat['machine'] = 'Laser'
            sol.extend(laser_sol)
        except ValueError as e:
            error_msg = str(e)
            if error_msg.startswith("no_solution:"):
                # Return error info for UI to display
                return {
                    "error": True,
                    "error_type": "no_solution",
                    "message": error_msg.replace("no_solution:", ""),
                    "current_params": {
                        "max_over_production": cint(order.max_over_production or 50),
                        "stock_length": stock_length,
                        "trim_cut": trim
                    }
                }
            raise
    
    # MCTĐ optimization (use mctd_blade_width from order)
    if mctd_lengths:
        if not order.steel_profile:
            frappe.throw("Vui lòng chọn Steel Profile khi có segment MCTĐ.")
        
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
            mctd_keys,  # Pass segment_keys for pattern mapping
            mctd_piece_names,
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
    # First, delete old Pattern Segments from database (child tables)
    old_patterns = frappe.get_all(
        "Cutting Pattern",
        filters={"parent": order.name, "parenttype": "Cutting Order"},
        pluck="name"
    )
    for pat_name in old_patterns:
        frappe.db.delete("Pattern Segment", {"parent": pat_name, "parenttype": "Cutting Pattern"})
    
    order.set("optimization_result", [])
    patterns_with_segments = []  # Store segments data for each pattern
    
    for pat in sol:
        # Build pattern string with piece names and machining details
        pattern_parts = []
        segments_data = []
        
        # pat['pattern'] keys are segment_keys: (length, segment_name, piece_code) tuples
        for segment_key, count in pat['pattern'].items():
            # segment_key is a tuple: (length, segment_name, piece_code)
            length = segment_key[0] if isinstance(segment_key, tuple) else segment_key
            
            # Get segment info using the full segment_key
            info = segment_info.get(segment_key, {})
            if not info and not isinstance(segment_key, tuple):
                # Fallback for old-style length-only keys
                info = segment_info.get((segment_key, f"{segment_key}mm"), {})
            
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
            
            # Format: "3x I5.1.2-497" (ngắn gọn - phương án C)
            length_str = f"{int(length)}" if length == int(length) else f"{length:.0f}"
            
            # Use piece_code short form (e.g., I5.1.2 from PHOI-I5.1.2)
            short_code = piece_code.replace("PHOI-", "") if piece_code else ""
            
            if short_code:
                pattern_parts.append(f"{count}x {short_code}-{length_str}")
            else:
                # Fallback: use segment_name
                pattern_parts.append(f"{count}x {segment_name}-{length_str}")
            
            # Build segment child data with FULL traceability
            segments_data.append({
                "piece_code": piece_code,  # Use calculated value (has fallback)
                "piece_name": piece_name,  # Use calculated value
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
        # Format: "3x I5.1.2-497" (ngắn gọn - phương án C)
        segments_summary_parts = []
        for seg in segments_data:
            segment_name = seg.get("segment_name", "") or f"{seg.get('length_mm', 0)}mm"
            piece_code = seg.get("piece_code", "")
            length = seg.get("length_mm", 0)
            qty = seg.get("quantity", 0)
            
            if qty > 0:
                length_str = f"{int(length)}" if length == int(length) else f"{length:.0f}"
                
                # Use piece_code short form (e.g., I5.1.2 from PHOI-I5.1.2)
                short_code = piece_code.replace("PHOI-", "") if piece_code else ""
                
                if short_code:
                    summary_part = f"{qty}x {short_code}-{length_str}"
                else:
                    summary_part = f"{qty}x {segment_name}-{length_str}"
                    
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
        sol, segment_keys, piece_names, demands, stock_length, order.enable_bundling
    )
    order.result_html = result_html
    order.save(ignore_permissions=True)
    
    # Return JSON-serializable result (sol contains tuple keys which can't be serialized)
    return {
        "success": True,
        "patterns_count": len(sol),
        "total_bars": sum(p.get("qty", 0) for p in sol),
        "message": f"Tối ưu thành công: {len(sol)} patterns, {sum(p.get('qty', 0) for p in sol)} cây sắt"
    }


def generate_result_html(patterns, segment_keys, piece_names, demands, stock_length, is_bundling=False):
    """
    Generate HTML display for optimization results
    
    Args:
        patterns: List of pattern dicts with 'pattern' (segment_key -> count), 'qty', 'waste'
        segment_keys: List of (length, segment_name) tuples
        piece_names: Dict mapping segment_key -> display name
        demands: List of quantities needed (same order as segment_keys)
    
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
    
    # Calculate production totals - use segment_keys as dict keys
    production = {sk: 0 for sk in segment_keys}
    for pat in patterns:
        for sk, c in pat['pattern'].items():
            if sk in production:
                production[sk] += c * pat['qty']
    
    # Summary table
    title = "TỔNG KẾT CẮT TỰ ĐỘNG" if is_bundling else "TỔNG KẾT CẮT LASER"
    html_parts.append(f"<h4>{title}</h4>")
    html_parts.append('<table class="table table-bordered table-sm" style="text-align:center">')
    html_parts.append('<thead><tr><th>Tên sắt</th><th>Đoạn (mm)</th><th>SL cần (đoạn)</th><th>SL cắt (đoạn)</th><th>Tồn kho (đoạn)</th></tr></thead>')
    html_parts.append('<tbody>')
    
    for i, sk in enumerate(segment_keys):
        length = sk[0] if isinstance(sk, tuple) else sk
        name = piece_names.get(sk, f"{length}mm")
        demand = demands[i]
        produced = production.get(sk, 0)
        surplus = produced - demand
        l_str = f"{int(length)}" if length == int(length) else f"{length:.1f}"
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
        # MCTD format: rows by waste, columns by segment_keys + bundle factors
        factors = sorted(set(pat.get('factor', 1) for pat in patterns), reverse=True)
        
        html_parts.append('<table class="table table-bordered table-sm" style="text-align:center; font-size:0.9em">')
        html_parts.append('<thead><tr><th>STT</th><th>Hao hụt (mm)</th>')
        
        for sk in segment_keys:
            length = sk[0] if isinstance(sk, tuple) else sk
            l_str = f"{int(length)}" if length == int(length) else f"{length:.1f}"
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
            
            for sk in segment_keys:
                count = pat['pattern'].get(sk, 0)
                if count > 0:
                    html_parts.append(f'<td style="font-weight:bold">{count}</td>')
                else:
                    html_parts.append('<td></td>')
            
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
        
        for sk in segment_keys:
            length = sk[0] if isinstance(sk, tuple) else sk
            name = piece_names.get(sk, "")
            l_str = f"{int(length)}" if length == int(length) else f"{length:.1f}"
            html_parts.append(f'<th style="min-width:60px">{name}<br>({l_str}mm)</th>')
        
        html_parts.append('<th>Hao hụt (mm)</th><th>SL cây sắt</th></tr></thead>')
        html_parts.append('<tbody>')
        
        for idx, pat in enumerate(patterns, 1):
            html_parts.append(f'<tr><td>{idx}</td>')
            
            for sk in segment_keys:
                count = pat['pattern'].get(sk, 0)
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


def solve_laser_cutting_stock(piece_lengths, demands, segment_keys, piece_names, stock_length, blade_width, trim, max_surplus, max_patterns=0):
    """
    Laser cutting optimization with multi-objective:
    1. Minimize total waste
    2. Minimize total surplus
    3. Minimize number of unique patterns (constrained by max_patterns)
    
    Args:
        piece_lengths: List of segment lengths (can have duplicates for same-length different-machining)
        demands: List of quantities needed for each segment
        segment_keys: List of (length, segment_name) tuples for pattern mapping
        piece_names: Dict mapping segment_key -> display name
        max_patterns: Maximum number of unique patterns allowed (0 = no limit)
    
    Returns:
        List of pattern dicts with 'pattern', 'qty', 'waste', 'used_length'
        where pattern dict keys are segment_keys (length, segment_name)
    """
    # Phase 1: Get patterns
    patterns = get_or_calculate_patterns(stock_length, piece_lengths, blade_width, 0.015, trim)
    
    if not patterns:
        frappe.throw("Không tìm được pattern nào phù hợp.")
    
    num_patterns = len(patterns)
    num_pieces = len(piece_lengths)
    
    # Phase 2: Optimize distribution with auto-retry
    # Cap upper bound to avoid INT32 overflow (max 2^31 - 1)
    MAX_INT32 = 2147483647
    total_demand = sum(demands)
    x_upper_bound = min(total_demand * 2, MAX_INT32)
    
    production = []
    surplus_vars = []
    
    # Auto-retry with increasing max_surplus if no solution found
    original_max_surplus = max_surplus
    retry_count = 0
    max_retries = 5
    
    while retry_count <= max_retries:
        model = cp_model.CpModel()
        x = [model.NewIntVar(0, x_upper_bound, f'x_{j}') for j in range(num_patterns)]
        production = []
        surplus_vars = []
        
        for i in range(num_pieces):
            # Production = sum(pattern_count[i] * x[j]) for all patterns j
            prod = sum(patterns[j][1][i] * x[j] for j in range(num_patterns))
            production.append(prod)
            
            # Surplus variable - limited to current max_surplus
            s = model.NewIntVar(0, max_surplus, f'surplus_{i}')
            model.Add(s == prod - demands[i])
            model.Add(prod >= demands[i])  # Must meet demand
            model.Add(s <= max_surplus)  # Limit per segment
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
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break  # Found solution
        
        # No solution - increase max_surplus and retry
        retry_count += 1
        if retry_count <= max_retries:
            max_surplus = max_surplus * 2  # Double the limit
            frappe.logger().info(f"No solution with max_surplus={max_surplus//2}, retrying with {max_surplus}")
        else:
            raise ValueError(f"no_solution:Không tìm được phương án cắt sau {max_retries} lần thử (max_surplus cuối={max_surplus}). Kiểm tra lại dữ liệu đầu vào.")
    
    min_waste = int(solver.ObjectiveValue())
    
    # Lock waste and minimize surplus
    model.Add(total_waste == min_waste)
    total_surplus = sum(surplus_vars)
    model.Minimize(total_surplus)
    
    # Add max_patterns constraint as simple upper bound (not a separate optimization phase)
    if max_patterns > 0:
        # Binary indicator: is pattern j used?
        pattern_used = [model.NewBoolVar(f'used_{j}') for j in range(num_patterns)]
        for j in range(num_patterns):
            model.Add(x[j] >= 1).OnlyEnforceIf(pattern_used[j])
            model.Add(x[j] == 0).OnlyEnforceIf(pattern_used[j].Not())
        total_patterns_used = sum(pattern_used)
        model.Add(total_patterns_used <= max_patterns)
    
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if max_patterns > 0:
            frappe.throw(f"Không tìm được phương án với max_patterns={max_patterns}. Thử tăng giới hạn pattern hoặc đặt = 0.")
        else:
            frappe.throw("Không tìm được phương án tối ưu tồn kho.")
    
    # Extract solution - use segment_keys as dict keys for correct mapping
    result_patterns = []
    for j in range(num_patterns):
        qty = solver.Value(x[j])
        if qty > 0:
            obj_value, sol = patterns[j]
            # CRITICAL: Use segment_keys as dict keys, not just lengths
            # This ensures correct mapping for same-length different-machining segments
            pattern_dict = {segment_keys[i]: sol[i] for i in range(num_pieces) if sol[i] > 0}
            
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


def solve_bundled_cutting_stock(piece_lengths, demands, segment_keys, piece_names, stock_length, blade_width, trim, 
                                 factors, manual_cut_limit, max_over, max_segments_per_pattern=5):
    """
    MCTĐ (Bundle cutting) optimization
    
    Phase 1: Generate patterns (max N different sizes from settings)
    Phase 2: Optimize bundle distribution with factors
    
    Args:
        piece_lengths: List of segment lengths
        demands: List of quantities needed
        segment_keys: List of (length, segment_name) tuples for pattern mapping
        piece_names: Dict mapping segment_key -> display name
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
    
    # Cap upper bound to avoid INT32 overflow
    MAX_INT32 = 2147483647
    total_demand = sum(demands)
    
    # Filter out factor 0
    pos_factors = [f for f in factors if f > 0]
    
    # Variables: b[pattern][factor] = number of bundles
    b = {}
    for j in range(num_patterns):
        for f in pos_factors:
            # Upper bound estimation with INT32 cap
            max_bundles = min(max(1, total_demand // f + 1), MAX_INT32)
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
                seg_name = piece_names.get(segment_keys[i], f"{piece_lengths[i]}mm")
                frappe.throw(f"Không thể đáp ứng nhu cầu cho đoạn {seg_name}")
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
    
    # Extract solution - use segment_keys as dict keys
    result_patterns = []
    for j in range(num_patterns):
        for f in pos_factors:
            num_bundles = solver.Value(b[(j, f)])
            if num_bundles > 0:
                obj_value, sol = patterns[j]
                # CRITICAL: Use segment_keys as dict keys for correct mapping
                pattern_dict = {segment_keys[i]: sol[i] for i in range(num_pieces) if sol[i] > 0}
                
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
