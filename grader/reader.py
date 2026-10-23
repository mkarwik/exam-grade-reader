"""Read student details and points from photos of graded exam pages with Gemini.

Each page goes through two requests:
1. find the student's name and index number (only title pages have them),
2. on title pages, read the points the lecturer wrote down (0-30, often circled).

Usage:
    export GEMINI_API_KEY=...
    python -m grader.reader photos/ results.json
"""

import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

MODEL_ID = "gemini-3.6-flash"
MAX_POINTS = 30
MAX_WORKERS = 5  # more parallel requests run into API rate limits

PROMPT_STUDENT = """
Wyciągnij dane ze strony pracy egzaminacyjnej.

Zwróć czysty obiekt JSON o polach:

{
    "imie_i_nazwisko": null,
    "nr_indeksu": null
}

- "imie_i_nazwisko" - imię i nazwisko znalezione na stronie. Jeżeli nie znajdziesz, zwróć null.
- "nr_indeksu" - liczba sześciocyfrowa. Jeżeli nie znajdziesz, zwróć null.

Uważaj przy rozpoznawaniu tekstu.
"""

PROMPT_POINTS = """
Wyciągnij dane: punkty (0-30).

Jest to liczba lub cyfra zapisana osobno od rozwiązania. Może być wzięta w kółko.
Uważaj - liczba może nachodzić na kółko.

Jeżeli nie jesteś pewny, a liczba jest wzięta w kółku, spróbuj zgadnąć, która część
jest liczbą, a która kółkiem, i rozpoznaj tylko tę część, która wygląda jak liczba.

Uważaj zwłaszcza na 0 - w kółku może wyglądać jak kółko w kółku.

Jeżeli uważasz, że na danej stronie nie ma zapisanej liczby punktów, zwróć null.

Zwróć WYŁĄCZNIE JSON:

{
    "punkty": liczba_lub_null
}
"""

RETRYABLE = ("429", "RESOURCE_EXHAUSTED", "500", "INTERNAL", "503", "UNAVAILABLE")


def make_client():
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set the GEMINI_API_KEY environment variable.")
    return genai.Client(api_key=api_key)


def ask(client, prompt, image, max_retries=7):
    """Send one prompt with one image; retry rate limits and server errors with backoff."""
    from google.genai import types

    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=MODEL_ID,
                contents=[prompt, image],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except Exception as e:  # the SDK raises different classes per transport
            if not any(code in str(e) for code in RETRYABLE) or attempt == max_retries - 1:
                raise
            wait = min(60, 2 ** attempt + random.uniform(0, 1))
            print(f"Rate limit or temporary error, retry {attempt + 1}/{max_retries} in {wait:.1f}s")
            time.sleep(wait)


def parse_json(text):
    """Parse the model's JSON answer, cutting it out of surrounding text if needed."""
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"Model returned no JSON: {text!r}")
        data = json.loads(text[start:end + 1])
    return data[0] if isinstance(data, list) else data


def clean_points(value):
    """Return points as a float in 0..MAX_POINTS, or None if missing or out of range."""
    if value is None or str(value).strip().lower() in ("", "none", "null"):
        return None
    try:
        points = float(value)
    except (TypeError, ValueError):
        return None
    return points if 0 <= points <= MAX_POINTS else None


def read_page(client, photo_path):
    image = Image.open(photo_path).convert("RGB")
    data = parse_json(ask(client, PROMPT_STUDENT, image).text)
    record = {
        "photo": photo_path,
        "imie_i_nazwisko": data.get("imie_i_nazwisko"),
        "nr_indeksu": data.get("nr_indeksu"),
        "punkty": None,
    }
    record["tytul"] = record["imie_i_nazwisko"] is not None or record["nr_indeksu"] is not None
    if record["tytul"]:
        record["punkty"] = clean_points(parse_json(ask(client, PROMPT_POINTS, image).text).get("punkty"))
    return record


def read_folder(folder, workers=MAX_WORKERS):
    client = make_client()
    photos = sorted(
        (os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))),
    )
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(read_page, client, p): p for p in photos}
        for future in as_completed(futures):
            path = futures[future]
            try:
                record = future.result()
                results.append(record)
                print(f"{os.path.basename(path)}: index={record['nr_indeksu']} points={record['punkty']}")
            except Exception as e:
                print(f"{os.path.basename(path)}: failed ({type(e).__name__}: {e})")
    results.sort(key=lambda r: r["photo"])
    return results


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python -m grader.reader PHOTO_FOLDER OUTPUT.json")
    out = read_folder(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(out)} pages to {sys.argv[2]}")
