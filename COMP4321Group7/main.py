import os, sqlite3, time
import nltk
nltk.download("wordnet")
from pathlib import Path
try: os.remove("./src/files/database.db")
except: pass

connection = sqlite3.connect(str(Path.cwd()) + "/COMP4321Group7/src/files/database.db", check_same_thread=False)
stopwords = open(str(Path.cwd()) + "/COMP4321Group7/stopwords.txt", 'r').read().split()
cursor = connection.cursor()

def init_database():
    tables = [
        ("relation", "child_id INTEGER [primary key], parent_id INTEGER"),
        ("id_url", "page_id INTEGER [primary key], url TEXT [primary key], UNIQUE (page_id, url) ON CONFLICT IGNORE"),
        ("word_id_word", "word_id INTEGER [primary key], word TEXT [primary key], UNIQUE (word_id, word) ON CONFLICT IGNORE"),
        ("inverted_idx", "page_id INTEGER, word_id INTEGER, count INTEGER, UNIQUE (page_id, word_id, count) ON CONFLICT IGNORE"),
        ("title_inverted_idx", "page_id INTEGER, word_id INTEGER, count INTEGER, UNIQUE (page_id, word_id, count) ON CONFLICT IGNORE"),
        ("page_info", "page_id INTEGER [primary key], size INTEGER, last_mod_date INTEGER, title TEXT, UNIQUE (page_id, size, last_mod_date, title) ON CONFLICT IGNORE"),
        ("page_id_word", "seq INTEGER, page_id INTEGER, word TEXT"),
        ("page_id_word_stem", "page_id INTEGER, word TEXT"),
        ("title_page_id_word_stem", "page_id INTEGER, word TEXT"),
        ("title_page_id_word", "seq INTEGER, page_id INTEGER, word TEXT"),
        ("title_forward_idx", "word_id INTEGER, count INTEGER, UNIQUE (word_id, count) ON CONFLICT REPLACE"),
        ("forward_idx", "word_id INTEGER, count INTEGER"),
        ("ranking", "page_id INTEGER [primary key], score REAL")
    ]
    for table, schema in tables:
        try: cursor.execute(f"CREATE TABLE {table} ({schema})")
        except sqlite3.OperationalError: pass
    connection.commit()

def create_file_from_db():
    from crawler import recursively_crawl, closeCrawler
    from indexer import indexer
    init_database()
    recursively_crawl(num_pages=300, url="https://www.cse.ust.hk/~kwtleung/COMP4321/testpage.htm")
    closeCrawler()
    indexer()

def main():
    create_file_from_db()
    connection.close()
    os.system("flask run")

if __name__ == '__main__':
    main()