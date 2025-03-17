# E-commerce Product URL Crawler

A scalable and efficient web crawler designed to discover product URLs across multiple e-commerce websites. This crawler uses asynchronous programming to handle multiple websites concurrently and implements intelligent URL discovery mechanisms.

## Features

- Asynchronous crawling for high performance
- Intelligent product URL detection
- Handles dynamic content and infinite scrolling
- Scalable to hundreds of domains
- Respects robots.txt and implements polite crawling
- Detailed logging and error handling
- Output in structured format

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd e-commerce-crawler
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Create a file containing your target domains (one per line) or pass them as command-line arguments:

```bash
python crawler.py --domains example1.com example2.com
# OR
python crawler.py --input domains.txt
```

2. The crawler will create an output directory with:
   - A JSON file mapping domains to their product URLs
   - Detailed logs of the crawling process
   - Statistics about the crawl

## Configuration

The crawler can be configured through environment variables or a .env file:

- `MAX_CONCURRENT_REQUESTS`: Maximum number of concurrent requests (default: 10)
- `CRAWL_DELAY`: Delay between requests to the same domain (default: 1.0)
- `MAX_DEPTH`: Maximum crawl depth (default: 3)
- `TIMEOUT`: Request timeout in seconds (default: 30)

## How It Works

1. **URL Discovery**: 
   - Analyzes URL patterns common in e-commerce sites
   - Uses heuristics to identify product pages
   - Implements breadth-first crawling strategy

2. **Performance Optimization**:
   - Asynchronous requests using aiohttp
   - Intelligent rate limiting per domain
   - Caching to avoid duplicate requests

3. **Robustness**:
   - Handles various edge cases
   - Implements retry mechanisms
   - Respects robots.txt directives

## Output Format

The crawler generates a JSON file with the following structure:

```json
{
  "domain1.com": {
    "product_urls": [
      "https://domain1.com/product/123",
      "https://domain1.com/item/456"
    ],
    "stats": {
      "total_urls_found": 100,
      "crawl_time": "2023-03-15 10:30:00",
      "depth_reached": 3
    }
  }
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 