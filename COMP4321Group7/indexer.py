from nltk.stem import PorterStemmer as Stemmer
import sqlite3
from zlib import crc32
from pathlib import Path
from itertools import chain
from collections import Counter
import numpy as np

ps = Stemmer()
stopwords = open(str(Path.cwd()) + "/COMP4321Group7/stopwords.txt", 'r').read().split()
connection = sqlite3.connect(str(Path.cwd()) + "/COMP4321Group7/src/files/database.db", check_same_thread=False)
cursor = connection.cursor()

def stemWords(words: list) -> list: return [ps.stem(word) for word in words]

def removeStopWords(words: list[str]) -> list[str]: return [word for word in words if word not in stopwords]

def populate_Ranking(scores: list[int], allPages: list[int]) -> None:
    cursor.execute("DELETE FROM ranking")
    cursor.executemany("INSERT INTO ranking(page_id,score) VALUES(?,?)", zip(allPages, scores))
    connection.commit()

def generateAdjacencyMatrix(allPages: list[int]) -> np.ndarray:
    matrixMap = {key: {val: 0 for val in allPages} for key in allPages}
    for page in allPages:
        children = cursor.execute("SELECT child_id FROM relation WHERE parent_id = ?", (page,)).fetchall()
        for child in children: matrixMap[page][child[0]] = 1
    return np.array([[val for val in matrixMap[key].values()] for key in matrixMap.keys()]).T

def ranking(curRankingScore: np.ndarray, adjacency_matrix: np.ndarray, teleportation_probability: float, max_iterations: int = 100) -> np.ndarray:
    ranking_scores = curRankingScore
    for _ in range(max_iterations):
        new_ranking_scores = adjacency_matrix.dot(ranking_scores)
        new_ranking_scores = teleportation_probability + (1 - teleportation_probability) * new_ranking_scores
        if np.allclose(ranking_scores, new_ranking_scores): break
        ranking_scores = new_ranking_scores
    return ranking_scores

def startRanking() -> None:
    allPages = [page[0] for page in cursor.execute("SELECT page_id FROM id_url").fetchall()]
    adjacencyMatrix = generateAdjacencyMatrix(allPages)
    RankingScores = ranking(np.ones(len(allPages)), adjacencyMatrix, 0.85)
    populate_Ranking(RankingScores, allPages)

def indexer():
    page_ids = cursor.execute("SELECT page_id FROM page_info").fetchall()
    for page_id in page_ids:
        cur_page_id = page_id[0]
        body_text = list(chain.from_iterable(cursor.execute("SELECT word FROM page_id_word WHERE page_id = ?", (cur_page_id,)).fetchall()))
        title_text = list(chain.from_iterable(cursor.execute("SELECT word FROM title_page_id_word WHERE page_id = ?", (cur_page_id,)).fetchall()))
        body_text = stemWords(removeStopWords(body_text))
        title_text = stemWords(removeStopWords(title_text))
        all_words = set(body_text + title_text)
        all_words_ids = [int(crc32(str.encode(w))) for w in all_words]
        word_id_word = list(zip(all_words_ids, all_words))
        page_id_word_stem = (cur_page_id, " ".join(body_text))
        title_id_word_stem = (cur_page_id, " ".join(title_text))
        cursor.executemany("INSERT INTO word_id_word VALUES (?, ?)", word_id_word)
        cursor.execute("INSERT INTO title_page_id_word_stem VALUES (?, ?)", title_id_word_stem)
        cursor.execute("INSERT INTO page_id_word_stem VALUES (?, ?)", page_id_word_stem)
        for element in Counter(body_text).items(): cursor.execute("INSERT INTO inverted_idx VALUES (?,?,?)", (cur_page_id, int(crc32(str.encode(element[0]))), element[1]))
        for element in Counter(title_text).items(): cursor.execute("INSERT INTO title_inverted_idx VALUES (?,?,?)", (cur_page_id, int(crc32(str.encode(element[0]))), element[1]))
        connection.commit()
    words = list(Counter(list(chain.from_iterable(cursor.execute("SELECT word_id FROM inverted_idx").fetchall()))).items())
    cursor.executemany("INSERT INTO forward_idx VALUES (?,?)", words)
    words = list(Counter(list(chain.from_iterable(cursor.execute("SELECT word_id FROM title_inverted_idx").fetchall()))).items())
    cursor.executemany("INSERT INTO title_forward_idx VALUES (?,?)", words)
    startRanking()
    connection.commit()
    connection.close()