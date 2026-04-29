from . import __version__ as app_version

app_name = "pos_general"
app_title = "POS General"
app_publisher = "Hussain"
app_description = "POS General"
app_email = "hussain@tabrah-holding.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/pos_general/css/pos_general.css"
# app_include_js = "/assets/pos_general/js/pos_general.js"

# include js, css files in header of web template
# web_include_css = "/assets/pos_general/css/pos_general.css"
# web_include_js = "/assets/pos_general/js/pos_general.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "pos_general/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Sales Order" : "public/js/sales_order_custom.js"}
doctype_js = {"Customer" : "public/js/customer_custom.js"}
doctype_js = {"POS Profile" : "public/js/pos_payment_method_custom.js"}
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice_custom.js",
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "pos_general.utils.jinja_methods",
#	"filters": "pos_general.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "pos_general.install.before_install"
# after_install = "pos_general.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "pos_general.uninstall.before_uninstall"
# after_uninstall = "pos_general.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "pos_general.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Sales Order": {
        "validate": "pos_general.custom.sales_order_custom.validate"
    },
    "Sales Invoice": {
        "before_save": "pos_general.custom.sales_invoice_custom.before_save_invoice",
        "on_submit": ["pos_general.custom.sales_invoice_custom.on_submit", "pos_general.custom.sales_invoice_custom.before_save_invoice"],
        "on_update": "pos_general.custom.sales_invoice_custom.on_update",
        "on_cancel": "pos_general.custom.sales_invoice_custom.on_cancel"
    },
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"pos_general.tasks.all"
#	],
#	"daily": [
#		"pos_general.tasks.daily"
#	],
#	"hourly": [
#		"pos_general.tasks.hourly"
#	],
#	"weekly": [
#		"pos_general.tasks.weekly"
#	],
#	"monthly": [
#		"pos_general.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "pos_general.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "pos_general.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Ducky apps
# override_doctype_dashboards = {
#	"Task": "pos_general.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["pos_general.utils.before_request"]
# after_request = ["pos_general.utils.after_request"]

# Job Events
# ----------
# before_job = ["pos_general.utils.before_job"]
# after_job = ["pos_general.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"pos_general.auth.validate"
# ]
