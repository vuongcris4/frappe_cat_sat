app_name = "cat_sat"
app_title = "Cat Sat"
app_publisher = "IEA"
app_description = "Ung dung quan ly cat sat"
app_email = "it@iea.com.vn"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "cat_sat",
# 		"logo": "/assets/cat_sat/logo.png",
# 		"title": "Cat Sat",
# 		"route": "/cat_sat",
# 		"has_permission": "cat_sat.api.permission.has_app_permission"
# 	}
# ]

patches = ["cat_sat.patches.v1_0_setup_steel_items"]
fixtures = ["Custom Field"]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cat_sat/css/cat_sat.css"
# app_include_js = "/assets/cat_sat/js/cat_sat.js"

# include js, css files in header of web template
# web_include_css = "/assets/cat_sat/css/cat_sat.css"
# web_include_js = "/assets/cat_sat/js/cat_sat.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cat_sat/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views

doctype_js = {
    "Item": "public/js/item_custom.js",
    "Production Plan": "public/js/production_plan.js",
    # "Cutting Order": [
    #     "public/js/cutting_pattern.js",
    #     "public/js/pattern_actions.js"
    # ]
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "cat_sat/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "cat_sat.utils.jinja_methods",
# 	"filters": "cat_sat.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "cat_sat.install.before_install"
# after_install = "cat_sat.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "cat_sat.uninstall.before_uninstall"
# after_uninstall = "cat_sat.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "cat_sat.utils.before_app_install"
# after_app_install = "cat_sat.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "cat_sat.utils.before_app_uninstall"
# after_app_uninstall = "cat_sat.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cat_sat.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {"Item": {"validate": "cat_sat.naming.set_variant_name"}}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cat_sat.tasks.all"
# 	],
# 	"daily": [
# 		"cat_sat.tasks.daily"
# 	],
# 	"hourly": [
# 		"cat_sat.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cat_sat.tasks.weekly"
# 	],
# 	"monthly": [
# 		"cat_sat.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "cat_sat.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "cat_sat.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cat_sat.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["cat_sat.utils.before_request"]
# after_request = ["cat_sat.utils.after_request"]

# Job Events
# ----------
# before_job = ["cat_sat.utils.before_job"]
# after_job = ["cat_sat.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"cat_sat.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
