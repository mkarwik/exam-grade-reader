"""Match what the model read (name, index number) to the official course roster.

Handwritten index numbers are often misread by a digit or two, so matching goes in three steps:
1. exact index number,
2. index within 3 edits: pick the candidate with the most similar name,
3. otherwise the most similar name, if similarity is above NAME_THRESHOLD.

Usage:
    python -m grader.matching results.json roster.json matched.json
"""

import json
import sys
from difflib import SequenceMatcher

MAX_INDEX_EDITS = 3
NAME_THRESHOLD = 0.7
NOT_FOUND = "nie_znaleziono"


def levenshtein(a, b):
    a, b = str(a), str(b)
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        current = [i + 1]
        for j, cb in enumerate(b):
            current.append(min(previous[j + 1] + 1, current[j] + 1, previous[j] + (ca != cb)))
        previous = current
    return previous[-1]


def name_similarity(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def find_student(index, name, roster):
    index = "" if index is None else str(index)
    name = "" if name is None else str(name)

    if index:
        for student in roster:
            if index == str(student["nr_indeksu"]):
                return student

        close = [s for s in roster if levenshtein(index, s["nr_indeksu"]) <= MAX_INDEX_EDITS]
        if close:
            return max(close, key=lambda s: name_similarity(name, s["imie_i_nazwisko"]))

    if name:
        best = max(roster, key=lambda s: name_similarity(name, s["imie_i_nazwisko"]), default=None)
        if best and name_similarity(name, best["imie_i_nazwisko"]) > NAME_THRESHOLD:
            return best

    return None


def match_results(results, roster):
    matched = []
    for row in results:
        student = find_student(row.get("nr_indeksu"), row.get("imie_i_nazwisko"), roster)
        row = dict(row)
        row["imie_i_nazwisko"] = student["imie_i_nazwisko"] if student else NOT_FOUND
        row["nr_indeksu"] = student["nr_indeksu"] if student else NOT_FOUND
        matched.append(row)
    return matched


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: python -m grader.matching RESULTS.json ROSTER.json OUTPUT.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        results = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        roster = json.load(f)
    out = match_results(results, roster)
    with open(sys.argv[3], "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    missing = sum(1 for r in out if r["nr_indeksu"] == NOT_FOUND)
    print(f"Matched {len(out) - missing}/{len(out)} pages; {missing} need manual check.")
