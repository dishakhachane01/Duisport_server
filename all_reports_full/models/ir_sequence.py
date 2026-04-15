import logging
_logger = logging.getLogger(__name__)

from odoo import models
from datetime import date as dt_date

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def _get_prefix(self, date=None, date_range=None):
        _logger.info("🔥 CUSTOM PREFIX METHOD CALLED")

        prefix = super()._get_prefix(date=date, date_range=date_range)

        journal_id = self._context.get('journal_id')

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)

            if journal.type == 'sale':
                dt = date or dt_date.today()

                if dt.month >= 4:
                    fy_start = dt.year
                    fy_end = dt.year + 1
                else:
                    fy_start = dt.year - 1
                    fy_end = dt.year

                return f"INV/{fy_start}-{fy_end}/"

        return prefix