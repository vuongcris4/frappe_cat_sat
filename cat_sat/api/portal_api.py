"""
Portal API endpoints for Worker Portal
"""
import frappe
import json
from frappe.utils import flt, cint
from collections import defaultdict


@frappe.whitelist(allow_guest=False)
def run_laser_optimization(data):
    """
    Run laser cutting optimization from portal
    
    Args:
        data: JSON string with:
            - steel_profile: Steel profile name
            - stock_length: Stock length in mm
            - trim_cut: Trim cut in mm
            - blade_width: Blade width in mm
            - max_surplus: Max surplus per segment
            - items: List of {segment_name, length_mm, qty, priority}
    
    Returns:
        Optimization result with HTML display
    """
    try:
        payload = json.loads(data)
        
        steel_profile = payload.get('steel_profile')
        stock_length = flt(payload.get('stock_length', 5850))
        trim_cut = flt(payload.get('trim_cut', 0))
        blade_width = flt(payload.get('blade_width', 1))
        max_surplus = cint(payload.get('max_surplus', 10))
        items = payload.get('items', [])
        
        if not items:
            return {"success": False, "error": "Không có đoạn sắt nào"}
        
        # Build demand map
        item_map = defaultdict(int)
        piece_names = {}
        for item in items:
            length = flt(item.get('length_mm'))
            qty = cint(item.get('qty'))
            name = item.get('segment_name') or f"{length}mm"
            
            if length > 0 and qty > 0:
                item_map[length] += qty
                if length not in piece_names:
                    piece_names[length] = name
        
        if not item_map:
            return {"success": False, "error": "Dữ liệu không hợp lệ"}
        
        piece_lengths = sorted(item_map.keys(), reverse=True)
        demands = [item_map[l] for l in piece_lengths]
        
        # Import optimization service
        from cat_sat.services.cutting_optimization_service import (
            solve_laser_cutting_stock,
            generate_result_html
        )
        
        # Run optimization
        sol = solve_laser_cutting_stock(
            piece_lengths,
            demands,
            piece_names,
            stock_length,
            blade_width,
            trim_cut,
            max_surplus
        )
        
        # Generate HTML result
        result_html = generate_result_html(
            sol, piece_lengths, piece_names, demands, stock_length, is_bundling=False
        )
        
        return {
            "success": True,
            "patterns": sol,
            "result_html": result_html,
            "total_bars": sum(p.get('qty', 0) for p in sol)
        }
        
    except Exception as e:
        frappe.log_error(f"Portal optimization error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def run_mctd_optimization(data):
    """
    Run MCTĐ (bundle) cutting optimization from portal
    """
    try:
        payload = json.loads(data)
        
        steel_profile = payload.get('steel_profile')
        stock_length = flt(payload.get('stock_length', 5850))
        trim_cut = flt(payload.get('trim_cut', 0))
        blade_width = flt(payload.get('blade_width', 2.5))
        max_surplus = cint(payload.get('max_surplus', 20))
        manual_cut_limit = cint(payload.get('manual_cut_limit', 10))
        items = payload.get('items', [])
        
        if not items:
            return {"success": False, "error": "Không có đoạn sắt nào"}
        
        # Get bundle factors from Steel Profile
        bundle_factors_str = frappe.db.get_value("Steel Profile", steel_profile, "bundle_factors")
        if not bundle_factors_str:
            return {"success": False, "error": f"Steel Profile '{steel_profile}' chưa có hệ số bó"}
        
        factors = [1]
        for f in bundle_factors_str.split():
            try:
                factor = int(f.strip())
                if factor > 1 and factor not in factors:
                    factors.append(factor)
            except ValueError:
                pass
        factors = sorted(set(factors), reverse=True)
        
        # Build demand map
        item_map = defaultdict(int)
        piece_names = {}
        for item in items:
            length = flt(item.get('length_mm'))
            qty = cint(item.get('qty'))
            name = item.get('segment_name') or f"{length}mm"
            
            if length > 0 and qty > 0:
                item_map[length] += qty
                if length not in piece_names:
                    piece_names[length] = name
        
        if not item_map:
            return {"success": False, "error": "Dữ liệu không hợp lệ"}
        
        piece_lengths = sorted(item_map.keys(), reverse=True)
        demands = [item_map[l] for l in piece_lengths]
        
        # Import optimization service
        from cat_sat.services.cutting_optimization_service import (
            solve_bundled_cutting_stock,
            generate_result_html
        )
        
        # Run optimization
        sol = solve_bundled_cutting_stock(
            piece_lengths,
            demands,
            piece_names,
            stock_length,
            blade_width,
            trim_cut,
            factors,
            manual_cut_limit,
            max_surplus
        )
        
        # Generate HTML result
        result_html = generate_result_html(
            sol, piece_lengths, piece_names, demands, stock_length, is_bundling=True
        )
        
        return {
            "success": True,
            "patterns": sol,
            "result_html": result_html,
            "total_bars": sum(p.get('qty', 0) for p in sol)
        }
        
    except Exception as e:
        frappe.log_error(f"MCTĐ optimization error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def get_steel_profiles():
    """Get all steel profiles for dropdown"""
    return frappe.get_all(
        "Steel Profile",
        fields=["name", "profile_code", "profile_name", "bundle_factors"],
        order_by="profile_code"
    )
