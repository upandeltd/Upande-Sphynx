app_name = "upande_sphynx"
app_title = "Upande Sphynx"
app_publisher = "Jeniffer"
app_description = "Upande Sphynx"
app_email = "okothjeniffer06@gmail.com"
app_license = "custom"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "upande_sphynx",
# 		"logo": "/assets/upande_sphynx/logo.png",
# 		"title": "Upande Sphynx",
# 		"route": "/upande_sphynx",
# 		"has_permission": "upande_sphynx.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/upande_sphynx/css/upande_sphynx.css"
# app_include_js = "/assets/upande_sphynx/js/upande_sphynx.js"

# include js, css files in header of web template
# web_include_css = "/assets/upande_sphynx/css/upande_sphynx.css"
# web_include_js = "/assets/upande_sphynx/js/upande_sphynx.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "upande_sphynx/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "upande_sphynx/public/icons.svg"

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
# 	"methods": "upande_sphynx.utils.jinja_methods",
# 	"filters": "upande_sphynx.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "upande_sphynx.install.before_install"
# after_install = "upande_sphynx.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "upande_sphynx.uninstall.before_uninstall"
# after_uninstall = "upande_sphynx.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "upande_sphynx.utils.before_app_install"
# after_app_install = "upande_sphynx.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "upande_sphynx.utils.before_app_uninstall"
# after_app_uninstall = "upande_sphynx.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "upande_sphynx.notifications.get_notification_config"

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

# doc_events = {
# hooks.py
doc_events = {
    "Share Transfer": {
        "validate": [
            "upande_sphynx.share_transfer_customization.share_transfer_controller.set_standard_accounts",
            "upande_sphynx.share_transfer_customization.share_transfer_controller.calculate_rate_and_amount",
            "upande_sphynx.share_transfer_customization.share_transfer_controller.validate_accounts"
            
        ],
        "before_submit": [
            "upande_sphynx.share_transfer_customization.share_transfer_controller.calculate_rate_and_amount",
            "upande_sphynx.share_transfer_customization.share_transfer_controller.validate_accounts"
        ]
        # Note: We're NOT calling create_custom_journal_entry on on_submit
        # Users will create JE manually via button
    }
    
    # ,

    # "Share Movement": {
    #     "validate": "upande_sphynx.doctype.share_movement.validate_share_movement"
    # }
}

# doc_events = {
#     "Share Transfer": {
#         # The 'validate' event runs before saving and before submitting
#        #"validate": "upande_sphynx.share_transfer_customization.share_transfer_controller.validate_share_transfer", 
        
#         # The 'on_submit' event runs after a document is submitted
#         # This is where you would call your custom JE creation logic
#         "on_submit": "upande_sphynx.share_transfer_customization.share_transfer_controller.create_custom_journal_entry"
#     }
# }

# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"upande_sphynx.tasks.all"
# 	],
# 	"daily": [
# 		"upande_sphynx.tasks.daily"
# 	],
# 	"hourly": [
# 		"upande_sphynx.tasks.hourly"
# 	],
# 	"weekly": [
# 		"upande_sphynx.tasks.weekly"
# 	],
# 	"monthly": [
# 		"upande_sphynx.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "upande_sphynx.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "upande_sphynx.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "upande_sphynx.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["upande_sphynx.utils.before_request"]
# after_request = ["upande_sphynx.utils.after_request"]

# Job Events
# ----------
# before_job = ["upande_sphynx.utils.before_job"]
# after_job = ["upande_sphynx.utils.after_job"]

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
# 	"upande_sphynx.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

