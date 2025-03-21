import re, math, requests, sqlite3, asyncio
from urllib.parse import urljoin, urlparse
from zlib import crc32
from bs4 import BeautifulSoup as bsoup
from email.utils import parsedate_to_datetime
from datetime import datetime
from pathlib import Path

connection = sqlite3.connect(str(Path.cwd()) + "/COMP4321Group7/src/files/database.db", check_same_thread=False)
cursor = connection.cursor()

async def get_soup(url: str) -> tuple[bsoup, int, int]:
    if not url.startswith(("https://", "http://")):
        url = "https://" + url
    try:
        request = requests.get(url, verify=False, timeout=15)
        last_modif = int(datetime.timestamp(parsedate_to_datetime(request.headers.get('last-modified', request.headers['Date']))))
        size = int(request.headers.get('content-length', len(request.content)))
        return bsoup(request.text, "lxml"), last_modif, size
    except (requests.exceptions.Timeout, Exception):
        return bsoup(""), 0, 0

def get_sub_link(url, soup):
    if not soup:
        return []
    return [f"{urlparse(urljoin(url, anchor['href'])).scheme}://{urlparse(urljoin(url, anchor['href'])).netloc}{urlparse(urljoin(url, anchor['href'])).path}".rstrip("/") for anchor in soup.findAll("a", href=True)]

def get_info(cur_url, soup, last_modif, parent_url=None):
    if not soup:
        return tuple()
    title = soup.title.get_text() if soup.title else ""
    cur_url_parsed = f"{urlparse(cur_url).scheme}://{urlparse(cur_url).netloc}{urlparse(cur_url).path}"
    parent_url_parsed = f"{urlparse(parent_url).scheme}://{urlparse(parent_url).netloc}{urlparse(parent_url).path}" if parent_url else None
    cur_page_id = crc32(str.encode(cur_url_parsed))
    parent_page_id = crc32(str.encode(parent_url_parsed)) if parent_url else 0
    for br in soup.select("br"):
        br.replace_with("\n")
    text = [re.sub("[^a-zA-Z-]+", "", word).lower() for word in soup.get_text().split() if word]
    return cur_page_id, parent_page_id, title, cur_url_parsed, last_modif, [(i, cur_page_id, word) for i, word in enumerate(text)]

def recursively_crawl(num_pages: int, url: str):
    queue, parent_links, visited = [url], [], []
    while num_pages > 0 and queue:
        cur_url, par_link = queue.pop(0), parent_links.pop(0) if parent_links else None
        visited.append(cur_url)
        soup, last_modif, size = asyncio.run(get_soup(cur_url))
        all_url = get_sub_link(cur_url, soup)
        for url in all_url:
            if url not in visited and url not in queue:
                queue.append(url)
                parent_links.append(cur_url)
            elif url in visited:
                insert_data_into_relation(crc32(str.encode(url)), crc32(str.encode(cur_url)))
                connection.commit()
        cur_page_id, parent_page_id, title, cur_url_parsed, last_modif, text = get_info(cur_url, soup, last_modif, par_link)
        result = cursor.execute("SELECT * FROM page_info WHERE page_id=?", (cur_page_id,)).fetchone()
        if result and (result[2] is None and last_modif is None or result[2] >= last_modif):
            print("Page crawling has been completed before! Skip crawling.")
            continue
        if result:
            cursor.execute("DELETE FROM relation WHERE parent_id = ?", (cur_page_id,))
            cursor.execute("DELETE FROM page_id_word WHERE page_id = ?", (cur_page_id,))
            cursor.execute("DELETE FROM page_info WHERE page_id = ?", (cur_page_id,))
            cursor.execute("DELETE FROM title_page_id_word WHERE page_id = ?", (cur_page_id,))
        insert_data_into_relation(cur_page_id, parent_page_id)
        insert_data_into_page_info(cur_page_id, size, last_modif, title)
        insert_data_into_id_url(cur_page_id, cur_url)
        insert_data_into_page_id_word(text)
        insert_data_into_title_page_id_word(title, cur_page_id)
        connection.commit()
        num_pages -= 1
    connection.commit()

def insert_data_into_relation(child, parent):
    cursor.execute("INSERT INTO relation VALUES (?,?)", (child, parent))

def insert_data_into_id_url(page_id, url):
    cursor.execute("INSERT INTO id_url VALUES (?,?)", (page_id, url))

def insert_data_into_page_info(page_id, size, last_modif, title):
    cursor.execute("INSERT INTO page_info VALUES (?,?,?,?)", (page_id, size, last_modif, title))

def insert_data_into_page_id_word(list_of_id):
    cursor.executemany("INSERT INTO page_id_word VALUES (?,?,?)", list_of_id)

def insert_data_into_title_page_id_word(title, page_id):
    title = [re.sub("[^a-zA-Z-]+", "", word) for word in title.split() if word]
    cursor.executemany("INSERT INTO title_page_id_word VALUES (?,?,?)", [(i, page_id, word) for i, word in enumerate(title)])

def closeCrawler():
    connection.close()