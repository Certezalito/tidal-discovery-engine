import unittest
from src.services import gemini_service


class TestGeminiService(unittest.TestCase):
    def test_cap_recommendations_enforces_upper_bound(self):
        recommendations = [
            {"artist": "A", "title": "1"},
            {"artist": "B", "title": "2"},
            {"artist": "C", "title": "3"},
        ]

        capped = gemini_service._cap_recommendations(recommendations, 2)
        self.assertEqual(len(capped), 2)
        self.assertEqual(capped[0]["artist"], "A")
        self.assertEqual(capped[1]["artist"], "B")

    def test_cap_recommendations_returns_empty_for_non_positive(self):
        recommendations = [{"artist": "A", "title": "1"}]
        self.assertEqual(gemini_service._cap_recommendations(recommendations, 0), [])
        self.assertEqual(gemini_service._cap_recommendations(recommendations, -3), [])

    def test_normalize_seed_track_supports_name_or_title(self):
        track_with_name = type(
            "TrackWithName",
            (),
            {"artist": type("Artist", (), {"name": "  Seed Artist  "})(), "name": "  Seed Song  "},
        )()

        normalized_name = gemini_service._normalize_seed_track(track_with_name)
        self.assertEqual(normalized_name["artist"], "Seed Artist")
        self.assertEqual(normalized_name["title"], "Seed Song")

        track_with_title = type(
            "TrackWithTitle",
            (),
            {"artist": type("Artist", (), {"name": "Artist 2"})(), "title": "Song 2"},
        )()

        normalized_title = gemini_service._normalize_seed_track(track_with_title)
        self.assertEqual(normalized_title["artist"], "Artist 2")
        self.assertEqual(normalized_title["title"], "Song 2")


if __name__ == "__main__":
    unittest.main()