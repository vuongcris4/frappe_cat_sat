from frappe import _

def get_data(data=None):
	return {
		"fieldname": "cutting_plan",
		"transactions": [
			{
				"label": _("Execution"),
				"items": ["Cutting Order"]
			}
		]
	}
