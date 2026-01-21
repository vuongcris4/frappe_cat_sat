import frappe

@frappe.whitelist()
def get_customer_skus(item_code):
    """Get all Customer SKU Mappings for a given item"""
    return frappe.get_all("Customer SKU Mapping", 
        filters={"item": item_code},
        fields=["customer_sku", "customer", "description", "barcode"]
    )
