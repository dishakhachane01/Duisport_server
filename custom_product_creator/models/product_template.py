from odoo import models, api, fields, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_create(self, name):
        if not self.env.user.has_group('custom_product_creator.group_product_creator'):
            raise UserError(
                _("You don't have permission to create new products. "
                  "Please contact your administrator to get 'Product Creator' access.")
            )
        return super().name_create(name)

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        return res

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """For 'create' operation, deny if user is not in the creator group."""
        if operation == 'create':
            if not self.env.user.has_group('custom_product_creator.group_product_creator'):
                if raise_exception:
                    raise UserError(
                        _("You don't have permission to create new products. "
                          "Please contact your administrator to get 'Product Creator' access.")
                    )
                return False
        return super().check_access_rights(operation, raise_exception=raise_exception)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_create(self, name):
        if not self.env.user.has_group('custom_product_creator.group_product_creator'):
            raise UserError(
                _("You don't have permission to create new products. "
                  "Please contact your administrator to get 'Product Creator' access.")
            )
        return super().name_create(name)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """For 'create' operation, deny if user is not in the creator group."""
        if operation == 'create':
            if not self.env.user.has_group('custom_product_creator.group_product_creator'):
                if raise_exception:
                    raise UserError(
                        _("You don't have permission to create new products. "
                          "Please contact your administrator to get 'Product Creator' access.")
                    )
                return False
        return super().check_access_rights(operation, raise_exception=raise_exception)