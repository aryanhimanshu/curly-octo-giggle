import asyncio
import argparse
import logging
from typing import List
import sys
import os
from dotenv import load_dotenv
from crawler.crawler import EcommerceCrawler
from crawler.parallel_crawler import ParallelCrawler
import multiprocessing

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_domains_from_file(file_path: str) -> List[str]:
    """
    Load domain list from a file.
    """
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading domains file: {str(e)}")
        sys.exit(1)

async def crawl_async(crawler: EcommerceCrawler, domains: List[str]):
    """
    Run crawler in async mode.
    """
    results = await crawler.crawl_domains(domains)
    return results

def crawl_parallel(crawler: ParallelCrawler, domains: List[str]):
    """
    Run crawler in parallel mode.
    """
    results = crawler.crawl(domains)
    return results

def print_results_summary(results: dict):
    """
    Print detailed summary of crawling results.
    """
    total_products = sum(
        len(result['product_urls'])
        for result in results.values()
    )
    
    logger.info("Crawling completed. Summary:")
    logger.info(f"Total product URLs found: {total_products}")
    
    for domain, result in results.items():
        stats = result.get('stats', {})
        urls_found = len(result.get('product_urls', []))
        urls_visited = stats.get('total_urls_visited', 0)
        depth = stats.get('depth_reached', 0)
        duration = stats.get('crawl_time', {}).get('duration_seconds', 0)
        
        logger.info(f"\nDomain: {domain}")
        logger.info(f"- Product URLs found: {urls_found}")
        logger.info(f"- Total URLs visited: {urls_visited}")
        logger.info(f"- Depth reached: {depth}")
        logger.info(f"- Duration: {duration:.2f} seconds")
        
        if 'error' in result:
            logger.warning(f"- Encountered error: {result['error']}")

def main():
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='E-commerce Product URL Crawler'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--domains',
        nargs='+',
        help='List of domains to crawl'
    )
    group.add_argument(
        '--input',
        type=str,
        help='Path to file containing domains (one per line)'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel processing (multiple processes)'
    )
    parser.add_argument(
        '--processes',
        type=int,
        default=multiprocessing.cpu_count(),
        help='Number of processes to use in parallel mode'
    )
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=int(os.getenv('MAX_CONCURRENT_REQUESTS', '10')),
        help='Maximum number of concurrent requests per process'
    )
    parser.add_argument(
        '--crawl-delay',
        type=float,
        default=float(os.getenv('CRAWL_DELAY', '1.0')),
        help='Delay between requests to the same domain'
    )
    parser.add_argument(
        '--max-depth',
        type=int,
        default=int(os.getenv('MAX_DEPTH', '3')),
        help='Maximum crawl depth'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=int(os.getenv('TIMEOUT', '30')),
        help='Request timeout in seconds'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Directory to store output files'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=int(os.getenv('MAX_RETRIES', '3')),
        help='Maximum number of retries for failed requests'
    )
    parser.add_argument(
        '--retry-delay',
        type=float,
        default=float(os.getenv('RETRY_DELAY', '2.0')),
        help='Initial delay between retries (will be exponentially increased)'
    )
    
    args = parser.parse_args()
    
    # Get domains list
    domains = (
        args.domains if args.domains
        else load_domains_from_file(args.input)
    )
    
    # Prepare crawler configuration
    crawler_config = {
        'max_concurrent_requests': args.max_concurrent,
        'crawl_delay': args.crawl_delay,
        'max_depth': args.max_depth,
        'timeout': args.timeout,
        'output_dir': args.output_dir,
        'max_retries': args.max_retries,
        'retry_delay': args.retry_delay
    }
    
    try:
        if args.parallel:
            logger.info(f"Starting parallel crawler with {args.processes} processes")
            crawler = ParallelCrawler(
                max_processes=args.processes,
                **crawler_config
            )
            results = crawl_parallel(crawler, domains)
        else:
            logger.info("Starting async crawler")
            crawler = EcommerceCrawler(**crawler_config)
            results = asyncio.run(crawl_async(crawler, domains))
        
        print_results_summary(results)
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 