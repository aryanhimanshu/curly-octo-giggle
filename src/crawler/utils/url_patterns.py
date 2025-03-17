import re
from typing import List, Pattern
from urllib.parse import urlparse

def get_common_product_patterns() -> List[Pattern]:
    """
    Returns a list of compiled regex patterns for common product URL formats.
    """
    patterns = [
        # Common product URL patterns
        r"/product[s]?/",
        r"/item[s]?/",
        r"/p/",
        r"/pd/",
        r"/dp/",  # Amazon style
        r"/[A-Za-z0-9-]+/[A-Za-z0-9-]+-p-\d+",  # Shopify style
        r"/catalog/product/view/id/\d+",  # Magento style
        r"/shop/[^/]+/\d+",
        r"/products/[^/]+$",
        # Add more patterns as needed
    ]
    
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

def is_product_url(url: str) -> bool:
    """
    Check if a URL is likely to be a product page based on common patterns.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if the URL matches product page patterns
    """
    # Parse the URL
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Skip obvious non-product URLs
    if any(path.startswith(prefix) for prefix in [
        '/cart',
        '/checkout',
        '/account',
        '/login',
        '/register',
        '/search',
        '/category',
        '/blog',
        '/about',
        '/contact',
        '/help',
        '/faq',
        '/terms',
        '/privacy',
    ]):
        return False
    
    # Check against common product URL patterns
    patterns = get_common_product_patterns()
    
    # Check if URL matches any product pattern
    return any(pattern.search(path) is not None for pattern in patterns)

def extract_product_id(url: str) -> str:
    """
    Attempt to extract a product ID from a URL.
    Returns empty string if no ID pattern is found.
    
    Args:
        url (str): Product URL
        
    Returns:
        str: Extracted product ID or empty string
    """
    patterns = [
        r'/product[s]?/(\d+)',
        r'/item[s]?/(\d+)',
        r'/p/(\d+)',
        r'/pd/(\d+)',
        r'/dp/([A-Z0-9]+)',  # Amazon style
        r'-p-(\d+)',  # Shopify style
        r'/id/(\d+)',  # Magento style
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "" 