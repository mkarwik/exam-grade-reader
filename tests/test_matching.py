import unittest

from grader.matching import NOT_FOUND, find_student, levenshtein, match_results
from grader.reader import clean_points, parse_json

# Invented students for tests only.
ROSTER = [
    {"imie_i_nazwisko": "Anna Kowalczyk", "nr_indeksu": 400101},
    {"imie_i_nazwisko": "Jan Wiśniewski", "nr_indeksu": 400102},
    {"imie_i_nazwisko": "Ola Nowak", "nr_indeksu": 412345},
]


class MatchingTest(unittest.TestCase):
    def test_exact_index(self):
        self.assertEqual(find_student("400102", "zupełnie inne", ROSTER)["imie_i_nazwisko"], "Jan Wiśniewski")

    def test_misread_index_uses_name_to_break_ties(self):
        # 400103 is one edit from both 400101 and 400102; the name decides
        self.assertEqual(find_student("400103", "Anna Kowalczyk", ROSTER)["nr_indeksu"], 400101)

    def test_name_only_when_index_unreadable(self):
        self.assertEqual(find_student(None, "Ola Nowk", ROSTER)["nr_indeksu"], 412345)

    def test_no_match_below_threshold(self):
        self.assertIsNone(find_student(None, "Xyz", ROSTER))

    def test_match_results_marks_missing(self):
        out = match_results([{"nr_indeksu": None, "imie_i_nazwisko": None, "punkty": 12.0}], ROSTER)
        self.assertEqual(out[0]["nr_indeksu"], NOT_FOUND)
        self.assertEqual(out[0]["punkty"], 12.0)

    def test_levenshtein(self):
        self.assertEqual(levenshtein("400101", "400101"), 0)
        self.assertEqual(levenshtein("400101", "400701"), 1)
        self.assertEqual(levenshtein("", "abc"), 3)


class ParsingTest(unittest.TestCase):
    def test_parse_json_with_extra_text(self):
        self.assertEqual(parse_json('Here you go: {"punkty": 17} done'), {"punkty": 17})

    def test_parse_json_list(self):
        self.assertEqual(parse_json('[{"punkty": 3}]'), {"punkty": 3})

    def test_clean_points(self):
        self.assertEqual(clean_points("17"), 17.0)
        self.assertIsNone(clean_points(None))
        self.assertIsNone(clean_points("null"))
        self.assertIsNone(clean_points(31))
        self.assertIsNone(clean_points("abc"))


if __name__ == "__main__":
    unittest.main()
