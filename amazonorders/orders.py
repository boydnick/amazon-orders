__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import asyncio
import concurrent.futures
import datetime
import logging
from typing import Any, Callable, List, Optional

from bs4 import Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.order import Order
from amazonorders.exception import AmazonOrdersError, AmazonOrdersNotFoundError
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


class AmazonOrders:
    """
    Using an authenticated :class:`~amazonorders.session.AmazonSession`, can be used to query Amazon
    for Order details and history.
    """

    def __init__(self,
                 amazon_session: AmazonSession,
                 debug: Optional[bool] = None,
                 config: Optional[AmazonOrdersConfig] = None) -> None:
        if not debug:
            debug = amazon_session.debug
        if not config:
            config = amazon_session.config

        #: The session to use for requests.
        self.amazon_session: AmazonSession = amazon_session
        #: The config to use.
        self.config: AmazonOrdersConfig = config

        #: Setting logger to ``DEBUG`` will send output to ``stderr``.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def get_order(self,
                  order_id: str,
                  clone: Optional[Order] = None) -> Order:
        """
        Get the full details for a given Amazon Order ID.

        :param order_id: The Amazon Order ID to lookup.
        :param clone: If a partially populated version of the Order has already been fetched from history.
        :return: The requested Order.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        meta = {"index": clone.index} if clone else None

        order_details_response = self.amazon_session.get(
            f"{self.config.constants.ORDER_DETAILS_URL}?orderID={order_id}")
        self.amazon_session.check_response(order_details_response, meta=meta)

        if not order_details_response.response.url.startswith(self.config.constants.ORDER_DETAILS_URL):
            raise AmazonOrdersNotFoundError(f"Amazon redirected, which likely means Order {order_id} was not found.",
                                            meta=meta)

        order_details_tag = util.select_one(order_details_response.parsed,
                                            self.config.selectors.ORDER_DETAILS_ENTITY_SELECTOR)

        if not order_details_tag:
            raise AmazonOrdersError(f"Could not parse details for Order {order_id}. Check if Amazon changed the HTML.")

        order: Order = self.config.order_cls(order_details_tag, self.config, full_details=True, clone=clone)

        return order

    def get_order_history(self,
                          year: int = datetime.date.today().year,
                          start_index: Optional[int] = None,
                          full_details: bool = False,
                          keep_paging: bool = True,
                          time_filter: Optional[str] = None) -> List[Order]:
        """
        Get the Amazon Order history for a given year or time period.

        :param year: The year for which to get history (ignored if time_filter is provided).
        :param start_index: The index of the Order from which to start fetching in the history. See
            :attr:`~amazonorders.entity.order.Order.index` to correlate, or if a call to this method previously errored
            out, see ``index`` in the exception's :attr:`~amazonorders.exception.AmazonOrdersError.meta` to continue
            paging where it left off.
        :param full_details: Get the full details for each Order in the history. This will execute an additional
            request per Order.
        :param keep_paging: ``False`` if only one page should be fetched.
        :param time_filter: Override year-based filtering. Supported values: 'last30', 'months-3', 'year-YYYY'.
        :return: A list of the requested Orders.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        # Use time_filter if provided, otherwise default to year-based filtering
        if time_filter:
            filter_param = time_filter
        else:
            filter_param = f"year-{year}"

        optional_start_index = f"&startIndex={start_index}" if start_index else ""
        next_page: Optional[str] = (
            "{url}?{query_param}={filter_param}{optional_start_index}"
        ).format(
            url=self.config.constants.ORDER_HISTORY_URL,
            query_param=self.config.constants.HISTORY_FILTER_QUERY_PARAM,
            filter_param=filter_param,
            optional_start_index=optional_start_index
        )

        current_index = int(start_index) if start_index else 0

        return asyncio.run(self._build_orders_async(next_page, keep_paging, full_details, current_index))

    def get_recent_orders(self,
                          days: int = 30,
                          full_details: bool = False,
                          keep_paging: bool = True) -> List[Order]:
        """
        Get recent Amazon Orders from the last N days using Amazon's native date filtering.
        This is much more efficient than year-based fetching for recent updates.
        
        **Deprecated**: Use get_order_history() with time_filter parameter instead.

        :param days: Number of days to go back (30, 90, or custom range).
        :param full_details: Get the full details for each Order in the history.
        :param keep_paging: ``False`` if only one page should be fetched.
        :return: A list of the requested Orders.
        """
        import warnings
        warnings.warn(
            "get_recent_orders() is deprecated. Use get_order_history() with time_filter parameter instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Use Amazon's native time filters for efficiency
        if days <= 30:
            time_filter = "last30"
        elif days <= 90:
            time_filter = "months-3"
        else:
            # For longer periods, fall back to year-based approach
            current_year = datetime.date.today().year
            return self.get_order_history(year=current_year, full_details=full_details, keep_paging=keep_paging)

        return self.get_order_history(time_filter=time_filter, full_details=full_details, keep_paging=keep_paging)

    async def _build_orders_async(self,
                                  next_page: Optional[str],
                                  keep_paging: bool,
                                  full_details: bool,
                                  current_index: int) -> List[Order]:
        order_tasks = []

        while next_page:
            page_response = self.amazon_session.get(next_page)
            self.amazon_session.check_response(page_response, meta={"index": current_index})

            order_tags = util.select(page_response.parsed,
                                     self.config.selectors.ORDER_HISTORY_ENTITY_SELECTOR)

            if not order_tags:
                order_count_tag = util.select_one(page_response.parsed,
                                                  self.config.selectors.ORDER_HISTORY_COUNT_SELECTOR)
                if order_count_tag and order_count_tag.text.startswith("0 "):
                    break
                else:
                    raise AmazonOrdersError("Could not parse Order history. Check if Amazon changed the HTML.")

            for order_tag in order_tags:
                order_tasks.append(self._async_wrapper(self._build_order, order_tag, full_details, current_index))

                current_index += 1

            next_page = None
            if keep_paging:
                next_page_tag = util.select_one(page_response.parsed,
                                                self.config.selectors.NEXT_PAGE_LINK_SELECTOR)
                if next_page_tag:
                    next_page = str(next_page_tag["href"])
                    if not next_page.startswith("http"):
                        next_page = f"{self.config.constants.BASE_URL}{next_page}"
                else:
                    logger.debug("No next page")
            else:
                logger.debug("keep_paging is False, not paging")

        return await asyncio.gather(*order_tasks)

    def _build_order(self,
                     order_tag: List[Tag],
                     full_details: bool,
                     current_index: int) -> Order:
        order: Order = self.config.order_cls(order_tag, self.config, index=current_index)

        if full_details:
            if len(util.select(order.parsed, self.config.selectors.ORDER_SKIP_ITEMS)) > 0:
                logger.warning(f"Order {order.order_number} was partially populated, "
                               f"since it is an unsupported Order type.")
            else:
                order = self.get_order(order.order_number, clone=order)

        return order

    async def _async_wrapper(self,
                             func: Callable,
                             *args: Any) -> Order:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.thread_pool_size) as pool:
            result = await loop.run_in_executor(pool, func, *args)
        return result
