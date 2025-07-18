__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Union, Optional

from amazonorders.exception import AmazonOrdersError
from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable

logger = logging.getLogger(__name__)


class Transaction(Parsable):
    """
    An Amazon Transaction.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig,
                 completed_date: date,
                 section_status: str = "Unknown") -> None:
        super().__init__(parsed, config)

        #: The Transaction completed date.
        self.completed_date: date = completed_date
        #: The Transaction payment method.
        self.payment_method: str = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_TRANSACTION_PAYMENT_METHOD_SELECTOR
        )
        #: The Transaction grand total.
        self.grand_total: float = self.safe_parse(self._parse_grand_total)
        #: The Transaction was a refund or not.
        self.is_refund: bool = self.grand_total > 0
        #: The Transaction Order number.
        self.order_number: str = self.safe_parse(self._parse_order_number)
        #: The Transaction Order details link.
        self.order_details_link: str = self.safe_parse(self._parse_order_details_link)
        #: The Transaction seller name.
        self.seller: str = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_TRANSACTION_SELLER_NAME_SELECTOR
        )
        #: The Transaction status.
        self.status: str = self.safe_parse(self._parse_status, section_status=section_status)

    def __repr__(self) -> str:
        return f"<Transaction {self.completed_date}: \"Order #{self.order_number}, Grand Total: {self.grand_total}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Transaction {self.completed_date}: Order #{self.order_number}, Grand Total: {self.grand_total}"

    def _parse_grand_total(self) -> Union[float, int]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_GRAND_TOTAL_SELECTOR)

        value = self.to_currency(value)

        if value is None:
            raise AmazonOrdersError(
                "Order.grand_total did not populate, but it's required. "
                "Check if Amazon changed the HTML."
            )  # pragma: no cover

        return value

    def _parse_order_number(self) -> str:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_ORDER_NUMBER_SELECTOR)

        if value is None:
            raise AmazonOrdersError(
                "Transaction.order_number did not populate, but it's required. "
                "Check if Amazon changed the HTML."
            )  # pragma: no cover

        match = re.match(".*#([0-9-]+)$", value)
        value = match.group(1) if match else ""

        return value

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_ORDER_LINK_SELECTOR, attr_name="href")

        if not value and self.order_number:
            value = f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_number}"

        return value

    def _parse_status(self, section_status: str) -> str:
        """
        Parse transaction status from individual transaction or section status.
        Returns one of: "pending", "completed", "refund"
        """
        # First check for individual transaction status (e.g., "Pending" in "In Progress" section)
        individual_status = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_STATUS_INDIVIDUAL_SELECTOR)
        if individual_status:
            individual_status = individual_status.strip().lower()
            if individual_status == "pending":
                return "pending"
        
        # Check if this is a refund based on order link text
        order_link_text = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_ORDER_LINK_SELECTOR)
        if order_link_text and "refund:" in order_link_text.lower():
            return "refund"
        
        # Fall back to section status
        section_status = section_status.strip().lower()
        if section_status == "completed":
            return "completed"
        elif section_status == "in progress":
            return "pending"
        else:
            # Default based on refund status for backwards compatibility
            return "refund" if self.is_refund else "completed"
