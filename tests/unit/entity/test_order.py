__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os

from amazonorders.entity.order import Order
from bs4 import BeautifulSoup
from tests.unittestcase import UnitTestCase


class TestOrder(UnitTestCase):
    def test_order_currency_stripped(self):
        # GIVEN
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", "order-currency-stripped-snippet.html"), encoding="utf-8"
        ) as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.subtotal, 1111.99)
        self.assertEqual(order.shipping_total, 2222.99)
        self.assertEqual(order.total_before_tax, 3333.99)
        self.assertEqual(order.estimated_tax, 4444.99)
        self.assertIsNone(order.refund_total)
        self.assertIsNone(order.subscription_discount)
        self.assertEqual(order.grand_total, 7777.99)

    def test_order_promotion_applied(self):
        # GIVEN
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", "order-promotion-applied-snippet.html"), encoding="utf-8"
        ) as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.promotion_applied, -0.05)

    def test_order_coupon_savings(self):
        # GIVEN
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", "order-details-coupon-savings.html"), encoding="utf-8"
        ) as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.coupon_savings, -3.89)

    def test_order_free_shipping(self):
        # GIVEN
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", "order-details-111-6778632-7354601.html"), encoding="utf-8"
        ) as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.free_shipping, -2.99)

    def test_order_coupon_savings_multiple(self):
        # GIVEN
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", "order-details-coupon-savings-multiple.html"), encoding="utf-8"
        ) as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.coupon_savings, -1.29)
