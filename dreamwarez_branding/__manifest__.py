{
    "name": "Dreamwarez Branding",
    "version": "1.0",
    "summary": "Replace Odoo branding with Dreamwarez",
    "depends": ["web"],
#     "data": [
#     "views/res_users.xml",
# ],
    "assets": {
        "web.assets_backend": [
            "dreamwarez_branding/static/src/js/branding.js",
        ],
    },
    "installable": True,
    "application": False,
}
