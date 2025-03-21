import sqlite3
import datetime
from pathlib import Path
from collections import defaultdict

connection = sqlite3.connect(str(Path.cwd()) + '/COMP4321Group7/src/files/database.db', check_same_thread=False)
cursor = connection.cursor()

def page_id_to_page_info(id: int) -> tuple[str, int, int]:
    page_info = cursor.execute("SELECT title, last_mod_date, size FROM page_info WHERE page_id = ?", (id,)).fetchone()
    if page_info is None:
        raise ValueError("No page with the given ID is found.")
    return page_info

def page_id_to_url(id: int) -> str:
    url = cursor.execute("SELECT url FROM id_url WHERE page_id = ?", (id,)).fetchone()
    if url is None:
        raise ValueError("No page with the given ID is found.")
    return url[0]

def page_id_to_stems(id: int, num_stems: int = 5, include_title: bool = True) -> list[tuple[str, int]]:
    stems_freqs = list(cursor.execute("SELECT word_id, count FROM inverted_idx WHERE page_id = ?", (id,)))
    if include_title:
        stems_freqs += list(cursor.execute("SELECT word_id, count FROM title_inverted_idx WHERE page_id = ?", (id,)))
    if not stems_freqs:
        raise ValueError("No page with the given ID is found.")
    
    stems_ids = [stem[0] for stem in stems_freqs]
    freqs = [stem[1] for stem in stems_freqs]
    stems = [cursor.execute("SELECT word FROM word_id_word WHERE word_id = ?", (stem_id,)).fetchone()[0] for stem_id in stems_ids]
    
    stems_counts = list(zip(stems, freqs))
    d = defaultdict(int)
    for k, v in stems_counts:
        d[k] += v
    return sorted(d.items(), key=lambda x: x[1], reverse=True)[0:num_stems]

def page_id_to_links(id: int, parent: bool = True) -> list[str]:
    link_ids = cursor.execute("SELECT parent_id FROM relation WHERE child_id = ?", (id,)).fetchall() if parent else cursor.execute("SELECT child_id FROM relation WHERE parent_id = ?", (id,)).fetchall()
    links = []
    for link_id in link_ids:
        try:
            links.append(page_id_to_url(link_id[0]))
        except ValueError:
            pass
    return links

def timestamp_to_datetime(timestamp: int):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

class SearchResult:
    def __init__(self, id: int, score: float, num_keywords: int = 5):
        self.id = id
        self.score = score
        self.title, self.time, self.size = page_id_to_page_info(id)
        self.time_formatted = timestamp_to_datetime(self.time)
        self.url = page_id_to_url(id)
        self.keywords = page_id_to_stems(id, num_keywords)
        self.parent_links = page_id_to_links(id, parent=True)
        self.child_links = page_id_to_links(id, parent=False)