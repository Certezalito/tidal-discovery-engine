import unittest
from unittest.mock import MagicMock, patch

from src.services import gemini_service


class TestGeminiService(unittest.TestCase):
    class _FakeParsed:
        def __init__(self, artist, title, isrc=None):
            self.artist = artist
            self.title = title
            self.isrc = isrc

        def model_dump(self):
            return {"artist": self.artist, "title": self.title, "isrc": self.isrc}

    class _FakePromptFeedback:
        def __init__(self, block_reason=None):
            self.block_reason = block_reason

    class _FakeCandidate:
        def __init__(self, finish_reason=None):
            self.finish_reason = finish_reason

    class _FakeResponse:
        def __init__(self, parsed=None, candidates=None, prompt_feedback=None):
            self.parsed = parsed
            self.candidates = candidates or []
            self.prompt_feedback = prompt_feedback

    class _FakeClientError(Exception):
        def __init__(self, message, code=None):
            super().__init__(message)
            self.code = code

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

    def test_classify_response_state_usable(self):
        response = self._FakeResponse(
            parsed=[self._FakeParsed("Artist A", "Track A", "USAAA0001")],
        )

        state, payload = gemini_service._classify_response_state(response)
        self.assertEqual(state, "usable")
        self.assertEqual(payload[0]["artist"], "Artist A")

    def test_classify_response_state_prompt_blocked(self):
        response = self._FakeResponse(
            parsed=[self._FakeParsed("Artist A", "Track A")],
            prompt_feedback=self._FakePromptFeedback(block_reason="SAFETY"),
        )

        state, payload = gemini_service._classify_response_state(response)
        self.assertEqual(state, "unusable-blocked")
        self.assertIn("prompt_feedback.block_reason", payload)

    def test_classify_response_state_finish_reason_blocked(self):
        response = self._FakeResponse(
            parsed=[self._FakeParsed("Artist A", "Track A")],
            candidates=[self._FakeCandidate(finish_reason="BLOCKLIST")],
        )

        state, payload = gemini_service._classify_response_state(response)
        self.assertEqual(state, "unusable-blocked")
        self.assertIn("candidate.finish_reason", payload)

    def test_retryable_status_code_classification(self):
        self.assertTrue(gemini_service._is_retryable_status_code(429))
        self.assertTrue(gemini_service._is_retryable_status_code(503))
        self.assertFalse(gemini_service._is_retryable_status_code(404))

    def test_generate_with_model_retries_unusable_response_once_then_succeeds(self):
        client = MagicMock()
        unusable = self._FakeResponse(parsed=[])
        usable = self._FakeResponse(parsed=[self._FakeParsed("Artist B", "Track B")])
        client.models.generate_content.side_effect = [unusable, usable]

        result = gemini_service._generate_recommendations_with_model(
            client,
            "gemini-test",
            "prompt",
            recovery_retries=1,
        )

        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(result[0]["artist"], "Artist B")

    def test_generate_with_model_valid_empty_fails_after_single_retry(self):
        client = MagicMock()
        client.models.generate_content.side_effect = [
            self._FakeResponse(parsed=[]),
            self._FakeResponse(parsed=[]),
        ]

        with self.assertRaises(ValueError) as ctx:
            gemini_service._generate_recommendations_with_model(
                client,
                "gemini-test",
                "prompt",
                recovery_retries=1,
            )

        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertIn("response-handling", str(ctx.exception))

    def test_generate_with_model_retries_retryable_client_error_once(self):
        client = MagicMock()
        retryable_error = self._FakeClientError("rate limited", code=429)
        usable = self._FakeResponse(parsed=[self._FakeParsed("Artist C", "Track C")])

        with patch.object(gemini_service.genai.errors, "ClientError", self._FakeClientError):
            client.models.generate_content.side_effect = [retryable_error, usable]
            result = gemini_service._generate_recommendations_with_model(
                client,
                "gemini-test",
                "prompt",
                recovery_retries=1,
            )

        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(result[0]["title"], "Track C")

    def test_generate_with_model_retryable_client_error_exhausted_raises(self):
        client = MagicMock()
        with patch.object(gemini_service.genai.errors, "ClientError", self._FakeClientError):
            client.models.generate_content.side_effect = [
                self._FakeClientError("rate limited", code=429),
                self._FakeClientError("still rate limited", code=429),
            ]

            with self.assertRaises(self._FakeClientError):
                gemini_service._generate_recommendations_with_model(
                    client,
                    "gemini-test",
                    "prompt",
                    recovery_retries=1,
                )

        self.assertEqual(client.models.generate_content.call_count, 2)

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    @patch("src.services.gemini_service._generate_recommendations_with_model")
    def test_get_recommendations_uses_configured_fallback_on_non_retryable_unavailable(
        self,
        mock_generate,
        mock_client,
        _mock_dotenv,
    ):
        seed_track = type(
            "SeedTrack",
            (),
            {"artist": type("Artist", (), {"name": "Seed Artist"})(), "name": "Seed Song"},
        )()

        with patch.object(gemini_service.genai.errors, "ClientError", self._FakeClientError):
            mock_generate.side_effect = [
                self._FakeClientError("model not found", code=404),
                [{"artist": "Fallback Artist", "title": "Fallback Track", "isrc": None}],
            ]

            with patch.dict(
                "os.environ",
                {
                    "GEMINI_MODEL": "primary-model",
                    "GEMINI_FALLBACK_MODEL": "fallback-model",
                },
                clear=False,
            ):
                result = gemini_service.get_recommendations(
                    api_key="test-key",
                    seed_tracks=[seed_track],
                    count=1,
                    shuffle=False,
                )

        self.assertEqual(result[0]["artist"], "Fallback Artist")
        self.assertEqual(mock_generate.call_count, 2)
        self.assertEqual(mock_generate.call_args_list[0].args[1], "primary-model")
        self.assertEqual(mock_generate.call_args_list[1].args[1], "fallback-model")

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    @patch("src.services.gemini_service._generate_recommendations_with_model")
    def test_get_recommendations_unavailable_without_fallback_raises_model_unavailable(
        self,
        mock_generate,
        mock_client,
        _mock_dotenv,
    ):
        seed_track = type(
            "SeedTrack",
            (),
            {"artist": type("Artist", (), {"name": "Seed Artist"})(), "name": "Seed Song"},
        )()

        with patch.object(gemini_service.genai.errors, "ClientError", self._FakeClientError):
            mock_generate.side_effect = self._FakeClientError("model not found", code=404)

            with patch.dict(
                "os.environ",
                {
                    "GEMINI_MODEL": "primary-model",
                },
                clear=False,
            ):
                with self.assertRaises(gemini_service.GeminiModelUnavailableError):
                    gemini_service.get_recommendations(
                        api_key="test-key",
                        seed_tracks=[seed_track],
                        count=1,
                        shuffle=False,
                    )


if __name__ == "__main__":
    unittest.main()