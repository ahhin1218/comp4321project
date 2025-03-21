from flask import Flask, render_template, make_response, request
import json
import retrieval
from util import SearchResult
import timeit
from typing import List

app = Flask(__name__)

@app.route("/")
def searchbar():
    history = json.loads(request.cookies.get('history', default = "{}"))
    return render_template("index.html", HISTORY = history)

@app.route("/search/", methods=['POST'])
def submit_search():
    query = request.form.get('searchbar') or request.form.get('history') or ""
    start_time = timeit.default_timer()
    search_results_raw = retrieval.search_engine(query)
    search_time_taken = timeit.default_timer() - start_time
    search_results = [SearchResult(ID, score) for ID, score in sorted(search_results_raw.items(), key = lambda x: x[1], reverse = True) if score != 0]

    history = json.loads(request.cookies.get('history', default = "[]"))
    if query and query not in history:
        history.append(query)

    resp = make_response(render_template("search_results.html", QUERY = query, RESULTS = search_results, TIME_TAKEN = search_time_taken, HISTORY = history))
    resp.set_cookie("history", json.dumps(history))
    return resp

if __name__ == "__main__":
    app.run(debug = True)