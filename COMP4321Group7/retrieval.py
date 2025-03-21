from pathlib import Path
import math, time, sqlite3, re
from nltk.stem import PorterStemmer as Stemmer
from collections import Counter

stopword = str(Path.cwd()) + '/COMP4321Group7/stopwords.txt'
connection = sqlite3.connect(str(Path.cwd()) + '/COMP4321Group7/src/files/database.db', check_same_thread=False)

MAX_RESULTS = 50
Title_globalPageDict, Text_globalPageDict = {}, {}
globalWordtoID, Title_globalPageStemText, Text_globalPageStemText = {}, {}, {}
cursor = connection.cursor()
DOCUMENT_COUNT = cursor.execute("SELECT COUNT(page_id) FROM id_url").fetchone()[0]
ps = Stemmer()
with open(stopword, 'r') as file: stopwords = file.read().split()

def parser(query: str) -> list[list[int]]:
    starting_time = time.time()
    single_word = [globalWordtoID[ps.stem(re.sub("[^a-zA-Z-]+", "", word.lower()))] for word in query.split()[:10000] if word.lower() not in stopwords and ps.stem(re.sub("[^a-zA-Z-]+", "", word.lower())) in globalWordtoID]
    phrases_no_stopword = [r"(?<!\S){}(?!\S)".format(" ".join(ps.stem(word) for word in phrase.lower().split() if word not in stopwords)) for phrase in re.findall('"([^"]*)"', query) if phrase]
    print(f"time taken for query: {time.time() - starting_time}")
    return [single_word, phrases_no_stopword]

def documentToVec(page_id: int, fromTitle: bool = False) -> dict[int, int]:
    table = "title_inverted_idx" if fromTitle else "inverted_idx"
    wordList = cursor.execute(f"SELECT word_id, count FROM {table} WHERE page_id = ?", (page_id,)).fetchall()
    maxTF = cursor.execute(f"SELECT MAX(count) FROM {table} WHERE page_id = ?", (page_id,)).fetchone()[0]
    forwardIdx = "title_forward_idx" if fromTitle else "forward_idx"
    word_counts = {word_id: count for word_id, count in cursor.execute(f"SELECT word_id, count FROM {forwardIdx} WHERE word_id IN ({','.join('?' for _ in wordList)})", [word for word, _ in wordList]).fetchall()}
    return {word: tf * math.log2(DOCUMENT_COUNT / word_counts[word]) / maxTF for word, tf in wordList} if wordList else {}

def queryToVec(queryEncoding: list[int]) -> dict[int, int]: return Counter(queryEncoding) if queryEncoding else {}

def cosinesimilarity(vector1: dict[int, int, int], vector2: dict[int, int, int]) -> float:
    commonwords = set(vector1.keys()) & set(vector2.keys())
    if not commonwords: return 0.0
    def normalize(vector):
        magnitude = math.sqrt(sum(value**2 for value in vector.values()))
        return {word: value / magnitude for word, value in vector.items()} if magnitude != 0 else vector
    vector1n = normalize(vector1)
    vector2n = normalize(vector2)
    dot_product = sum(vector1n[word] * vector2n[word] for word in commonwords)
    # cosine_similarity = dot_product / (magnitude1 * magnitude2)
    score = dot_product * 50
    return score

def phraseFilter(document_id: int, phrases: list[str]) -> bool:
    return all(re.search(phrase, Title_globalPageStemText[document_id]) or re.search(phrase, Text_globalPageStemText[document_id]) for phrase in phrases) if phrases else True

def queryFilter(document_id: int, query: list[int]) -> bool:
    return any(word in Title_globalPageDict[document_id] or word in Text_globalPageDict[document_id] for word in query) if query else True

def search_engine(query: str) -> dict[int, float]:
    if not query: return {}
    splitted_query = parser(query)
    if not splitted_query[0]: return {}
    vector1 = queryToVec(splitted_query[0])
    title_cosinescores, text_cosinescores = {}, {}
    for document in allDocs:
        document = document[0]
        if splitted_query[1] and not phraseFilter(document, splitted_query[1]): continue
        if not queryFilter(document, splitted_query[0]): continue
        title_vector2, text_vector2 = Title_globalPageDict[document], Text_globalPageDict[document]
        title_cosinescores[document] = cosinesimilarity(vector1, title_vector2)
        text_cosinescores[document] = cosinesimilarity(vector1, text_vector2)
    def normalize_scores(scores: dict[int, float]) -> dict[int, float]:
        max_score = max(scores.values(), default=1)
        return {key: (value / max_score) * 50 for key, value in scores.items()} if max_score != 0 else scores
    title_cosinescores = normalize_scores(title_cosinescores)
    text_cosinescores = normalize_scores(text_cosinescores)
    title_cosinescores = dict(sorted(title_cosinescores.items(), key=lambda item: item[1], reverse=True)[:MAX_RESULTS])
    text_cosinescores = dict(sorted(text_cosinescores.items(), key=lambda item: item[1], reverse=True)[:MAX_RESULTS])
    combined_Scores = {key: 0.33 * title_cosinescores.get(key, 0) + 0.7 * text_cosinescores.get(key, 0) for key in set(title_cosinescores) | set(text_cosinescores)}
    RankingScore = {page_id: score for page_id, score in cursor.execute(f"SELECT page_id, score FROM ranking WHERE page_id IN ({','.join('?' for _ in combined_Scores)})", tuple(combined_Scores.keys())).fetchall()}
    combined_Scores = {page_id: score * RankingScore.get(page_id, 0) for page_id, score in combined_Scores.items()}
    scores = normalize_scores(combined_Scores)
    return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True)[:MAX_RESULTS])

allDocs = cursor.execute("SELECT page_id FROM id_url").fetchall()
for doc in allDocs:
    doc = doc[0]
    Title_globalPageDict[doc] = documentToVec(doc, True)
    Text_globalPageDict[doc] = documentToVec(doc)
    Title_globalPageStemText[doc] = cursor.execute("SELECT word FROM title_page_id_word_stem WHERE page_id = ?", (doc,)).fetchone()[0]
    Text_globalPageStemText[doc] = cursor.execute("SELECT word FROM page_id_word_stem WHERE page_id = ?", (doc,)).fetchone()[0]
globalWordtoID = {word: word_id for word_id, word in cursor.execute("SELECT word_id, word FROM word_id_word").fetchall()}