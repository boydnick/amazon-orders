# Amazon Orders API Reference

## Official Documentation
- **Upstream docs**: https://amazon-orders.readthedocs.io/
- **GitHub repo**: https://github.com/alexdlaird/amazon-orders

## Fork Modifications
This fork includes the following modifications from the upstream project:

### Regional Support
- Added support for Amazon Canada (`.ca` domain)
- Extended region detection and URL handling

### Transaction Parsing Enhancements
- Added transaction status categorization:
  - **complete**: Actual charges that have been processed
  - **in-progress**: Authorization holds that may not result in charges
- Added transaction completeness detection:
  - **complete**: Transaction amount matches order total
  - **partial**: Transaction represents partial shipment/charge

### API Method Signatures

#### `get_order_history()`
```python
def get_order_history(
    self,
    year: int = datetime.date.today().year,
    start_index: int | None = None,
    full_details: bool = False,
    keep_paging: bool = True,
    time_filter: str | None = None,
) -> list[Order]:
```

**Parameters:**
- `year`: Year to fetch orders for (default: current year, ignored if time_filter is provided)
- `start_index`: Starting index for pagination (default: None)
- `full_details`: Fetch complete order details (default: False)
- `keep_paging`: Continue fetching all pages (default: True)
- `time_filter`: Override year-based filtering (default: None)

**Supported time_filter Values:**
- `'last30'`: Last 30 days (most efficient for recent orders)
- `'months-3'`: Past 3 months (good for quarterly updates)
- `'year-YYYY'`: Specific year (e.g., 'year-2024')
- `None`: Uses year parameter (default behavior)

**Important Notes:**
- NEW: Now supports efficient date range filtering via time_filter parameter
- `last30` and `months-3` filters are much more efficient than year-based filtering
- Does NOT support `days` parameter (use time_filter instead)

#### `get_transactions()`
```python
def get_transactions(self, days: int = 365, ...):
```

**Parameters:**
- `days`: Number of days back to fetch transactions (default: 365)

### Amazon Web Interface Filters
The following filters are available in Amazon's web interface but not in the API:
- `last30`: Last 30 days
- `months-3`: Past 3 months
- `year-YYYY`: Specific years
- `archived`: Archived orders

### Usage Examples

```python
# Get last 30 days orders (most efficient for recent data)
orders = amazon_orders.get_order_history(time_filter="last30")

# Get past 3 months orders (good for quarterly updates)
orders = amazon_orders.get_order_history(time_filter="months-3")

# Get current year orders (traditional approach)
orders = amazon_orders.get_order_history(year=2024)
# or equivalently:
orders = amazon_orders.get_order_history(time_filter="year-2024")

# Get orders with full details using efficient filtering
orders = amazon_orders.get_order_history(time_filter="last30", full_details=True)

# Get transactions for last 90 days
transactions = amazon_orders.get_transactions(days=90)
```

### Efficiency Recommendations

For regular script execution (biweekly to monthly):
- Use `time_filter="last30"` for most runs
- Use `time_filter="months-3"` for catchup after longer gaps
- Only use year-based filtering for historical data or maintenance

## Development Notes
- Rate limiting: Amazon enforces rate limits - implement retry logic with exponential backoff
- Session management: Sessions expire - implement re-authentication logic
- Error handling: Handle redirect errors and timeout scenarios
- Regional differences: Account for different Amazon domains and layouts