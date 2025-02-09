import re
import trafilatura

def read_markdown_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    return markdown_content


def scrape(url:str):
    html_content = trafilatura.fetch_url(url)
    return trafilatura.extract(html_content,include_images=True,include_links=True,include_tables=True)

def extract_python_code(text:str):
    pattern = r'```python\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return text
    