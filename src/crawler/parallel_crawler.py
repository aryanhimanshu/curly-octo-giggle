import multiprocessing
import asyncio
from typing import List, Dict
import os
import json
from datetime import datetime
import logging
from .crawler import EcommerceCrawler

logger = logging.getLogger(__name__)

def crawl_domain_wrapper(args):
    """
    Wrapper function to run crawler in a separate process.
    """
    domain, config = args
    
    # Set up asyncio event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Initialize crawler with config
    crawler = EcommerceCrawler(**config)
    
    try:
        # Run crawler for single domain
        result = loop.run_until_complete(crawler.crawl_domains([domain]))
        return domain, result[domain]
    except Exception as e:
        logger.error(f"Error crawling {domain}: {str(e)}")
        return domain, {
            "product_urls": [],
            "error": str(e),
            "stats": {
                "crawl_time": datetime.now().isoformat(),
                "status": "failed"
            }
        }
    finally:
        loop.close()

class ParallelCrawler:
    def __init__(
        self,
        max_processes: int = None,
        **crawler_config
    ):
        """
        Initialize parallel crawler.
        
        Args:
            max_processes: Maximum number of processes to use. Defaults to CPU count.
            **crawler_config: Configuration to pass to each EcommerceCrawler instance.
        """
        self.max_processes = max_processes or multiprocessing.cpu_count()
        self.crawler_config = crawler_config

    def crawl(self, domains: List[str]) -> Dict[str, Dict]:
        """
        Crawl multiple domains in parallel using multiple processes.
        
        Args:
            domains: List of domains to crawl
            
        Returns:
            Dict mapping domains to their crawl results
        """
        logger.info(f"Starting parallel crawler with {self.max_processes} processes")
        
        # Create process pool
        with multiprocessing.Pool(processes=self.max_processes) as pool:
            # Prepare arguments for each process
            args = [(domain, self.crawler_config) for domain in domains]
            
            # Map domains to processes and get results
            results = dict(pool.map(crawl_domain_wrapper, args))
            
            # Save results
            self._save_results(results)
            
            return results

    def _save_results(self, results: Dict[str, Dict]) -> None:
        """
        Save crawling results to a JSON file.
        """
        output_dir = self.crawler_config.get('output_dir', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(
            output_dir,
            f"parallel_crawl_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}") 