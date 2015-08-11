# This file is part of sale_cart_discount module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.config import config as config_

__all__ = ['SaleCart']
__metaclass__ = PoolMeta

STATES = {
    'readonly': (Eval('state') != 'draft')
    }
DIGITS = config_.getint('product', 'price_decimal', default=4)
DISCOUNT_DIGITS = config_.getint('product', 'discount_decimal', default=4)


class SaleCart:
    __name__ = 'sale.cart'
    gross_unit_price = fields.Numeric('Gross Price', digits=(16, DIGITS),
        states=STATES)
    discount = fields.Numeric('Discount', digits=(16, DISCOUNT_DIGITS),
        states=STATES)

    @classmethod
    def __setup__(cls):
        super(SaleCart, cls).__setup__()
        cls.unit_price.states['readonly'] = True
        cls.unit_price.digits = (20, DIGITS + DISCOUNT_DIGITS)
        if 'discount' not in cls.product.on_change:
            cls.product.on_change.add('discount')
        if 'discount' not in cls.untaxed_amount.on_change_with:
            cls.untaxed_amount.on_change_with.add('discount')
        if 'gross_unit_price' not in cls.untaxed_amount.on_change_with:
            cls.untaxed_amount.on_change_with.add('gross_unit_price')
        if 'discount' not in cls.quantity.on_change:
            cls.quantity.on_change.add('discount')

    @staticmethod
    def default_discount():
        return Decimal(0)

    def update_prices(self):
        unit_price = None
        gross_unit_price = self.gross_unit_price
        if self.gross_unit_price is not None and self.discount is not None:
            unit_price = self.gross_unit_price * (1 - self.discount)
            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

            if self.discount != 1:
                gross_unit_price = unit_price / (1 - self.discount)
            digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price.quantize(
                Decimal(str(10.0 ** -digits)))
        return {
            'gross_unit_price': gross_unit_price,
            'unit_price': unit_price,
            }

    @fields.depends('gross_unit_price', 'discount')
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'discount')
    def on_change_discount(self):
        return self.update_prices()

    def on_change_product(self):
        Product = Pool().get('product.product')

        res = super(SaleCart, self).on_change_product()
        if self.product:
            context = {}
            if self.party:
                context['customer'] = self.party.id
            if self.party and self.party.sale_price_list:
                context['price_list'] = self.party.sale_price_list.id

            with Transaction().set_context(context):
                res['gross_unit_price'] = Product.get_sale_price([self.product],
                        self.quantity or 0)[self.product.id]
            self.gross_unit_price = res['gross_unit_price']
        if 'unit_price' in res and 'gross_unit_price' in res:
            self.discount = Decimal(0)
            res.update(self.update_prices())
        if 'discount' not in res:
            res['discount'] = Decimal(0)
        return res

    def on_change_quantity(self):
        res = super(SaleCart, self).on_change_quantity()
        if 'unit_price' in res:
            self.gross_unit_price = res['unit_price']
            res.update(self.update_prices())
        return res
