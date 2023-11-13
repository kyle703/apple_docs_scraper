import validators
import selenium.webdriver
import PyPDF2
import time
import random
import yaml
import logging
import base64
import html2text
from tqdm import tqdm
from collections import namedtuple
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Setting up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define a named tuple for URL processing
URLTask = namedtuple('URLTask', ['filename', 'url'])

def random_wiggle():
    base_sleep = 4
    wiggle = random.uniform(-0.5, 1.5)
    return base_sleep + wiggle

def load_url_tasks_from_yaml(file_path):
    """Load URL tasks from a YAML file."""
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
            url_tasks = []
            for section, data in config.items():
                base_url = data['base_url']
                for url in data['urls']:
                    full_url = base_url + url
                    filename = f"{section}_{url.replace('/', '_')}"
                    url_tasks.append(URLTask(filename, full_url))
            return url_tasks
    except Exception as e:
        logging.error(f"Error loading YAML file: {e}")
        return []

class URLValidator:
    @staticmethod
    def validate(url):
        """Validate the given URL."""
        return validators.url(url)

class WebpageToPDFConverter:
    @staticmethod
    def convert(url, output_path, content_selector="#main > div.doc-content-wrapper > div.doc-content"):
        """Convert a webpage to a PDF file, focusing on specific content."""
        try:
            options = selenium.webdriver.ChromeOptions()
            options.headless = True
            user_agents = [
                # List of user agents for simulating different browsers
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0"
            ]
            options.add_argument(f"user-agent={random.choice(user_agents)}")

            with selenium.webdriver.Chrome(options=options) as driver:
                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, content_selector)))

                time.sleep(random_wiggle())
                # Hide all elements other than the desired content
                hide_script = f"document.querySelectorAll('body > *').forEach(el => {{ if (!el.querySelector('{content_selector}')) {{ el.style.display = 'none'; }} }});"
                driver.execute_script(hide_script)

                time.sleep(random_wiggle())
                # Generate PDF only of the visible content
                pdf = driver.execute_cdp_cmd("Page.printToPDF", {'printBackground': True})
                with open(output_path, 'wb') as file:
                    file.write(base64.b64decode(pdf['data']))
        except Exception as e:
            logging.error(f"Error in WebpageToPDFConverter for URL {url}: {e}")


class WebpageToMarkdownConverter:
    @staticmethod
    def convert(url, markdown_path, content_selector="#main > div.doc-content-wrapper > div.doc-content"):
        try:
            options = selenium.webdriver.ChromeOptions()
            # Ensure headless mode is correctly set
            options.add_argument("--headless")
            # ... User-Agent and other options ...

            with selenium.webdriver.Chrome(options=options) as driver:
                logging.info(f"Processing URL: {url}")
                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, content_selector)))
                logging.info(f"Page loaded successfully. Extracting content from: {content_selector}")

                content_html = driver.find_element(By.CSS_SELECTOR, content_selector).get_attribute('outerHTML')
                markdown = html2text.html2text(content_html)
                with open(markdown_path, 'w', encoding='utf-8') as file:
                    file.write(markdown)
                logging.info(f"Markdown content saved to {markdown_path}")
        except Exception as e:
            logging.error(f"Error in WebpageToMarkdownConverter for URL {url}: {e}")



class PDFToMarkdownConverter:
    @staticmethod
    def convert(pdf_path, markdown_path):
        """Convert a PDF file to a Markdown file."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() + '\n\n'

            with open(markdown_path, 'w') as file:
                file.write(text)
        except Exception as e:
            logging.error(f"Error in PDFToMarkdownConverter: {e}")

class URLProcessor:
    def __init__(self, url_tasks, output_dir='output'):
        self.url_tasks = url_tasks
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def process(self):
        limit = 1
        for task in tqdm(self.url_tasks, desc="Processing URLs", unit="url"):
            if limit == 0:
                logging.info("Max limit reached")
                break
            if URLValidator.validate(task.url):
                pdf_path = self.output_dir / f"{task.filename}.pdf"
                markdown_path = self.output_dir / f"{task.filename}.md"

                logging.info(f"executing url task: {task.filename} @ {task.url}")
                
                WebpageToMarkdownConverter.convert(task.url, markdown_path)

                time.sleep(random_wiggle())

                limit -= 1
            else:
                logging.warning(f"Invalid URL skipped: {task.url}")


    

if __name__ == "__main__":
    try:
        url_tasks = load_url_tasks_from_yaml('url_tasks.yaml')
        processor = URLProcessor(url_tasks)
        processor.process()
    except Exception as e:
        logging.error(f"Error in URLProcessor: {e}")