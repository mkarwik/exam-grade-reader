# Exam grade reader

A prototype that reads grades from scanned exam papers, so lecturers do not have to type them in by hand and students can see their own exam without coming to office hours.

Built as part of the Uczelnie Przyszłości programme at the University of Warsaw.

## The problem

I surveyed 30 lecturers and 80+ students. Lecturers spend **20–30 minutes per student group** typing grades into the university system, and hold **1–2 extra office hours** only so students can look at their marked exams.

## What it does

1. Takes photos or scans of graded exam pages.
2. Sends each page to the Gemini API in two steps: first it finds the student's name and index number, then, on title pages, it reads the points the lecturer wrote down (often circled, sometimes overlapping the circle).
3. Matches what it read to the course roster. Handwritten index numbers are often off by a digit, so matching goes from exact index, to a close index plus the most similar name, to name only.
4. Shows each page next to the extracted data, so the lecturer reviews and confirms grades instead of typing them in (in the notebook).

The model only reads the handwriting. Everything around it is part of this project: the two-step reading flow, validating what comes back (points must fall in the allowed range), correcting misread index numbers against the roster, the review step and the retry logic for API rate limits. It has been tested on more than 100 real exam papers.

**Next:** sending each student a scan of their own exam and uploading grades to the university's student records system.

## How I got here

I started with a classic computer-vision pipeline: whitening scans with adaptive thresholding, removing printed lines with the Hough transform, separating ink colours with PCA, then EasyOCR to find text and Microsoft's TrOCR handwriting model restricted to digits. None of these approaches was reliable enough on real exams, where points are circled, overlap the circle or sit next to the solution.

A multimodal LLM handled these cases far better with a short, specific prompt, so the current version uses Gemini. The earlier experiments are kept in [`notebooks/experiments.ipynb`](notebooks/experiments.ipynb).

## Running it

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...                            # from Google AI Studio
python -m grader.reader photos/ results.json         # read every page in the folder
python -m grader.matching results.json roster.json matched.json
python -m unittest discover -s tests -t .            # tests for matching and parsing
```

`roster.json` is a list of `{"imie_i_nazwisko": ..., "nr_indeksu": ...}` objects exported from the course list.

## Privacy

Exam photos, rosters and results contain students' personal data. None of it is in this repository, and `.gitignore` blocks image and JSON files so it cannot be committed by accident.

## Status

Working prototype, now being tested on real exams.

Author: [Maciej Karwik](https://github.com/mkarwik)
