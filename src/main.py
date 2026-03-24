import sys
import json
from pathlib import Path
from scraper import WebScraper
from logger import Logger

def main():
    config_path = Path("config/config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    logger = Logger(config['log']['directory'])
    scraper = WebScraper(config, logger)

    try:
        scraper.run()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
