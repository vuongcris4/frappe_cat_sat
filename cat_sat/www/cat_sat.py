import frappe


def get_context(context):
    """Context for Cat Sat main portal page"""
    context.no_cache = 1
    context.show_sidebar = False
    return context
