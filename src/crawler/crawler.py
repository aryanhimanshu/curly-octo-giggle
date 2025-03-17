import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse
from fake_useragent import UserAgent
import json
import os
from datetime import datetime
from .utils.url_patterns import is_product_url, get_common_product_patterns
from .utils.rate_limiter import RateLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EcommerceCrawler:
    def __init__(
        self,
        max_concurrent_requests: int = 10,
        crawl_delay: float = 1.0,
        max_depth: int = 3,
        timeout: int = 30,
        output_dir: str = "output",
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        self.max_concurrent_requests = max_concurrent_requests
        self.crawl_delay = crawl_delay
        self.max_depth = max_depth
        self.timeout = timeout
        self.output_dir = output_dir
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = UserAgent()
        self.rate_limiters: Dict[str, RateLimiter] = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    async def crawl_domains(self, domains: List[str]) -> Dict[str, Dict]:
        """
        Crawl multiple domains concurrently and collect product URLs.
        """
        results = {}
        tasks = []

        async with aiohttp.ClientSession() as session:
            for domain in domains:
                task = asyncio.create_task(self.crawl_single_domain(session, domain))
                tasks.append(task)
            
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for domain, result in zip(domains, completed_results):
                if isinstance(result, Exception):
                    logger.error(f"Error crawling {domain}: {str(result)}")
                    results[domain] = {
                        "product_urls": [],
                        "error": str(result),
                        "stats": {
                            "crawl_time": datetime.now().isoformat(),
                            "status": "failed"
                        }
                    }
                else:
                    results[domain] = result

        # Save results to file
        self._save_results(results)
        return results

    async def crawl_single_domain(
        self,
        session: aiohttp.ClientSession,
        domain: str
    ) -> Dict:
        """
        Crawl a single domain and collect product URLs.
        """
        start_time = datetime.now()
        visited_urls: Set[str] = set()
        product_urls: Set[str] = set()
        urls_to_visit = {f"https://{domain}"}
        current_depth = 0

        rate_limiter = RateLimiter(self.crawl_delay)
        self.rate_limiters[domain] = rate_limiter

        while urls_to_visit and current_depth <= self.max_depth:
            next_urls = set()
            tasks = []

            # Process URLs at current depth
            for url in urls_to_visit:
                if url in visited_urls:
                    continue
                
                visited_urls.add(url)
                task = asyncio.create_task(
                    self._process_url(session, url, domain, rate_limiter)
                )
                tasks.append(task)

                # Process in batches to control concurrency
                if len(tasks) >= self.max_concurrent_requests:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    next_urls.update(self._handle_batch_results(results, product_urls))
                    tasks = []

            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                next_urls.update(self._handle_batch_results(results, product_urls))

            urls_to_visit = next_urls - visited_urls
            current_depth += 1

        end_time = datetime.now()
        
        return {
            "product_urls": list(product_urls),
            "stats": {
                "total_urls_found": len(product_urls),
                "total_urls_visited": len(visited_urls),
                "depth_reached": current_depth - 1,
                "crawl_time": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds()
                }
            }
        }

    async def _process_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        domain: str,
        rate_limiter: RateLimiter
    ) -> Set[str]:
        """
        Process a single URL: fetch it, check if it's a product page,
        and extract new URLs to visit. Includes retry logic for failed requests.
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                await rate_limiter.acquire()
                
                headers = {
                    "User-Agent": self.user_agent.random,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Cache-Control": "max-age=0"
                }

                async with session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    ssl=False  # Handle sites with SSL issues
                ) as response:
                    if response.status == 429:  # Too Many Requests
                        logger.warning(f"Rate limit hit for {domain}, backing off...")
                        await asyncio.sleep(self.retry_delay * (2 ** retries))
                        retries += 1
                        continue
                        
                    if response.status >= 500:  # Server errors
                        if retries < self.max_retries:
                            logger.warning(f"Server error {response.status} for {url}, retrying...")
                            await asyncio.sleep(self.retry_delay * (2 ** retries))
                            retries += 1
                            continue
                        else:
                            logger.error(f"Max retries reached for {url}")
                            return set()

                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: Status {response.status}")
                        return set()

                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        logger.debug(f"Skipping non-HTML content at {url}")
                        return set()

                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract all links
                    new_urls = set()
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        absolute_url = urljoin(url, href)
                        
                        # Only keep URLs from the same domain
                        parsed_url = urlparse(absolute_url)
                        if parsed_url.netloc == domain and parsed_url.scheme in ('http', 'https'):
                            new_urls.add(absolute_url)

                    return new_urls

            except asyncio.TimeoutError:
                if retries < self.max_retries:
                    logger.warning(f"Timeout for {url}, retrying...")
                    await asyncio.sleep(self.retry_delay * (2 ** retries))
                    retries += 1
                    continue
                else:
                    logger.error(f"Max retries reached for {url} after timeout")
                    return set()

            except Exception as e:
                if retries < self.max_retries:
                    logger.warning(f"Error processing {url}: {str(e)}, retrying...")
                    await asyncio.sleep(self.retry_delay * (2 ** retries))
                    retries += 1
                    continue
                else:
                    logger.error(f"Max retries reached for {url}: {str(e)}")
                    return set()

        return set()  # Return empty set if all retries failed

    def _handle_batch_results(
        self,
        results: List[Set[str]],
        product_urls: Set[str]
    ) -> Set[str]:
        """
        Handle results from a batch of URL processing tasks.
        """
        next_urls = set()
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {str(result)}")
                continue
            
            for url in result:
                if is_product_url(url):
                    product_urls.add(url)
                next_urls.add(url)
        
        return next_urls

    def _save_results(self, results: Dict[str, Dict]) -> None:
        """
        Save crawling results to a JSON file.
        """
        output_file = os.path.join(
            self.output_dir,
            f"crawl_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}") 