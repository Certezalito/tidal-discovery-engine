import json
import os
import threading
import unittest
from unittest.mock import MagicMock, patch

from src.services import gemini_service


class TestGeminiService(unittest.TestCase):
    class _FakeInteraction:
        """Minimal test double mimicking a google-genai Interactions API Interaction response."""

        def __init__(self, output_text=None, status="completed", error=None, steps=None):
            self.output_text = output_text
            self.status = status
            self.error = error
            self.steps = steps or []

    class _FakeClientError(Exception):
        def __init__(self, message, code=None, status_code=None):
            super().__init__(message)
            self.code = code
            self.status_code = status_code

    class _FakeInteractionsStatusError(Exception):
        """Mimics google-genai 3.x Interactions APIStatusError (uses .status_code, not genai.errors)."""

        def __init__(self, message, status_code):
            super().__init__(message)
            self.status_code = status_code

    class _FakeAPITimeoutError(Exception):
        """Mimics google-genai 3.x Interactions APITimeoutError."""

    @classmethod
    def _rec_interaction(cls, songs, status="completed", error=None):
        payload = json.dumps({"songs": songs})
        return cls._FakeInteraction(output_text=payload, status=status, error=error)

    @classmethod
    def _genre_interaction(cls, classifications, status="completed", error=None):
        payload = json.dumps({"classifications": classifications})
        return cls._FakeInteraction(output_text=payload, status=status, error=error)

    def setUp(self):
        self._sleep_patcher = patch("src.services.gemini_service.time.sleep")
        self._mock_sleep = self._sleep_patcher.start()
        self.addCleanup(self._sleep_patcher.stop)

        # Isolate environment from local .env values for deterministic testing
        for var in [
            "GEMINI_MODEL",
            "GEMINI_FALLBACK_MODEL",
            "GEMINI_ORGANIZE_MODEL",
            "GEMINI_SERVICE_TIER",
            "GEMINI_FLEX_FALLBACK_STANDARD",
            "GEMINI_SERVICE_TIER_FALLBACK",
            "GEMINI_FLEX_TIMEOUT_SECONDS",
            "GEMINI_FLEX_MAX_RETRIES",
        ]:
            if var in os.environ:
                orig_val = os.environ.pop(var)
                self.addCleanup(os.environ.__setitem__, var, orig_val)

    # ------------------------------------------------------------------
    # Normalization, Schema & Grounding Tests (US1, Principle VIII)
    # ------------------------------------------------------------------

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

    def test_song_schema_excludes_isrc_for_zero_hallucination(self):
        schema = gemini_service.RecommendationList.model_json_schema()
        song_props = schema["$defs"]["Song"]["properties"]
        self.assertEqual(set(song_props.keys()), {"artist", "title"})
        self.assertNotIn("isrc", song_props)

    # ------------------------------------------------------------------
    # Interactions Response State & Extraction Tests (Phase 2, US1)
    # ------------------------------------------------------------------

    def test_classify_response_state_usable(self):
        interaction = self._rec_interaction([{"artist": "Artist A", "title": "Track A"}])

        state, payload = gemini_service._classify_response_state(interaction)
        self.assertEqual(state, "usable")
        self.assertEqual(payload, [{"artist": "Artist A", "title": "Track A"}])
        self.assertNotIn("isrc", payload[0])

    def test_classify_response_state_extracts_from_model_output_steps_fallback(self):
        interaction = self._FakeInteraction(
            output_text=None,
            status="completed",
            steps=[
                {"type": "thought", "signature": "sig-1"},
                {
                    "type": "model_output",
                    "content": [
                        {"type": "text", "text": '{"songs": [{"artist": "Step Artist", "title": "Step Song"}]}'}
                    ],
                },
            ],
        )

        state, payload = gemini_service._classify_response_state(interaction)
        self.assertEqual(state, "usable")
        self.assertEqual(payload, [{"artist": "Step Artist", "title": "Step Song"}])

    def test_classify_response_state_failed_status_is_blocked(self):
        interaction = self._FakeInteraction(
            output_text=None,
            status="failed",
            error="SAFETY_FILTER",
        )

        state, payload = gemini_service._classify_response_state(interaction)
        self.assertEqual(state, "unusable-blocked")
        self.assertIn("interaction.status=failed", payload)

    def test_classify_response_state_cancelled_status_is_blocked(self):
        interaction = self._FakeInteraction(output_text=None, status="cancelled")

        state, payload = gemini_service._classify_response_state(interaction)
        self.assertEqual(state, "unusable-blocked")
        self.assertIn("interaction.status=cancelled", payload)

    def test_classify_response_state_malformed_json_is_unusable_empty(self):
        interaction = self._FakeInteraction(output_text="not-valid-json")

        state, payload = gemini_service._classify_response_state(interaction)
        self.assertEqual(state, "unusable-empty")
        self.assertIn("invalid structured recommendation JSON", payload)

    def test_retryable_status_code_classification(self):
        self.assertTrue(gemini_service._is_retryable_status_code(429))
        self.assertTrue(gemini_service._is_retryable_status_code(503))
        self.assertFalse(gemini_service._is_retryable_status_code(404))

    # ------------------------------------------------------------------
    # US1: Interactions API Recommendations Tests
    # ------------------------------------------------------------------

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_get_recommendations_uses_interactions_api_with_store_false_and_neon_low_thinking(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._rec_interaction(
            [{"artist": "Burial", "title": "Untrue"}]
        )

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Burial"})(), "name": "Archangel"})()
        results = gemini_service.get_recommendations("test-key", [seed_track], 5, shuffle=True)

        self.assertEqual(results, [{"artist": "Burial", "title": "Untrue"}])
        mock_client_class.assert_called_once_with(
            api_key="test-key",
            http_options={"timeout": 120_000, "api_version": "v1beta"},
        )
        mock_client.models.generate_content.assert_not_called()
        mock_client.interactions.create.assert_called_once()

        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["model"], "gemini-4-neon")
        self.assertIs(kwargs["store"], False)
        self.assertEqual(kwargs["service_tier"], "standard")
        self.assertEqual(kwargs["generation_config"], {"thinking_level": "low"})
        self.assertNotIn("temperature", kwargs["generation_config"])
        self.assertNotIn("top_p", kwargs["generation_config"])
        self.assertNotIn("top_k", kwargs["generation_config"])
        self.assertEqual(kwargs["response_format"]["type"], "text")
        self.assertEqual(kwargs["response_format"]["mime_type"], "application/json")
        self.assertEqual(
            kwargs["response_format"]["schema"],
            gemini_service.RecommendationList.model_json_schema(),
        )
        self.assertIn("Deep Cuts", kwargs["input"])

    def test_generate_with_model_retries_unusable_response_once_then_succeeds(self):
        client = MagicMock()
        unusable = self._FakeInteraction(output_text=None)
        usable = self._rec_interaction([{"artist": "Artist B", "title": "Track B"}])
        client.interactions.create.side_effect = [unusable, usable]

        result = gemini_service._generate_recommendations_with_model(
            client,
            "gemini-test",
            "prompt",
            recovery_retries=1,
        )

        self.assertEqual(client.interactions.create.call_count, 2)
        self.assertEqual(result[0]["artist"], "Artist B")

    def test_generate_with_model_valid_empty_fails_after_single_retry(self):
        client = MagicMock()
        client.interactions.create.side_effect = [
            self._FakeInteraction(output_text=None),
            self._FakeInteraction(output_text=None),
        ]

        with self.assertRaises(ValueError) as ctx:
            gemini_service._generate_recommendations_with_model(
                client,
                "gemini-test",
                "prompt",
                recovery_retries=1,
            )

        self.assertEqual(client.interactions.create.call_count, 2)
        self.assertIn("response-handling", str(ctx.exception))

    def test_generate_with_model_retries_retryable_client_error_once(self):
        client = MagicMock()
        retryable_error = self._FakeInteractionsStatusError("rate limited", status_code=429)
        usable = self._rec_interaction([{"artist": "Artist C", "title": "Track C"}])

        client.interactions.create.side_effect = [retryable_error, usable]
        result = gemini_service._generate_recommendations_with_model(
            client,
            "gemini-test",
            "prompt",
            recovery_retries=1,
        )

        self.assertEqual(client.interactions.create.call_count, 2)
        self.assertEqual(result[0]["title"], "Track C")

    def test_generate_with_model_retryable_client_error_exhausted_raises(self):
        client = MagicMock()
        client.interactions.create.side_effect = [
            self._FakeInteractionsStatusError("rate limited", status_code=429),
            self._FakeInteractionsStatusError("still rate limited", status_code=429),
        ]

        with self.assertRaises(self._FakeInteractionsStatusError):
            gemini_service._generate_recommendations_with_model(
                client,
                "gemini-test",
                "prompt",
                recovery_retries=1,
            )

        self.assertEqual(client.interactions.create.call_count, 2)

    # ------------------------------------------------------------------
    # US3: Model Resolution, Deprecated Model Substitution & Fallback
    # ------------------------------------------------------------------

    def test_resolve_primary_model_defaults_to_gemini_flash_latest(self):
        with patch.dict("os.environ", {}, clear=True):
            model, source = gemini_service._resolve_primary_model({})
            self.assertEqual(model, "gemini-flash-latest")
            self.assertEqual(source, "default")

    def test_resolve_primary_model_aliases(self):
        for alias in ["latest", "LATEST", "auto", "Auto", "flash-latest"]:
            with patch.dict("os.environ", {"GEMINI_MODEL": alias}, clear=True):
                model, source = gemini_service._resolve_primary_model({})
                self.assertEqual(model, "gemini-flash-latest")
                self.assertEqual(source, "env")

    def test_resolve_primary_model_explicit_current_model(self):
        for current_model in ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview"]:
            with patch.dict("os.environ", {"GEMINI_MODEL": current_model}, clear=True):
                model, source = gemini_service._resolve_primary_model({})
                self.assertEqual(model, current_model)
                self.assertEqual(source, "env")

    def test_resolve_primary_model_substitutes_deprecated_legacy_models_with_warning(self):
        deprecated_models = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]
        for legacy in deprecated_models:
            with patch.dict("os.environ", {"GEMINI_MODEL": legacy}, clear=True):
                with self.assertLogs(level="WARNING") as cm:
                    model, source = gemini_service._resolve_primary_model({})
                self.assertEqual(model, "gemini-flash-latest")
                self.assertEqual(source, "env")
                self.assertTrue(
                    any(legacy in msg and "gemini-flash-latest" in msg for msg in cm.output),
                    f"Expected deprecation warning for {legacy}",
                )

    def test_resolve_fallback_model_substitutes_deprecated_legacy_model_with_warning(self):
        with patch.dict("os.environ", {"GEMINI_FALLBACK_MODEL": "gemini-2.0-flash"}, clear=True):
            with self.assertLogs(level="WARNING") as cm:
                fallback = gemini_service._resolve_fallback_model({})
            self.assertEqual(fallback, "gemini-flash-latest")
            self.assertTrue(any("GEMINI_FALLBACK_MODEL" in msg and "gemini-2.0-flash" in msg for msg in cm.output))

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

        mock_generate.side_effect = [
            self._FakeInteractionsStatusError("model not found", status_code=404),
            [{"artist": "Fallback Artist", "title": "Fallback Track"}],
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
    def test_get_recommendations_raises_model_unavailable_error_for_radio_lastfm_fallback(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.side_effect = self._FakeInteractionsStatusError(
            "Model not found", status_code=404
        )
        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "A"})(), "name": "S"})()

        with patch.dict("os.environ", {"GEMINI_MODEL": "missing-custom-model"}, clear=True):
            with self.assertRaises(gemini_service.GeminiModelUnavailableError) as ctx:
                gemini_service.get_recommendations("test-key", [seed_track], 5)

        self.assertIn("category='unavailable/not-found'", str(ctx.exception))

    # ------------------------------------------------------------------
    # US2: Interactions API Genre Classification Tests
    # ------------------------------------------------------------------

    def test_resolve_organize_model_precedence_and_deprecation(self):
        # Defaults to gemini-flash-latest when neither GEMINI_ORGANIZE_MODEL nor GEMINI_MODEL is set
        with patch.dict("os.environ", {}, clear=True):
            model, source = gemini_service._resolve_organize_model({})
            self.assertEqual(model, "gemini-flash-latest")
            self.assertEqual(source, "default")

        # GEMINI_ORGANIZE_MODEL overrides GEMINI_MODEL
        with patch.dict(
            "os.environ",
            {"GEMINI_MODEL": "gemini-4-neon", "GEMINI_ORGANIZE_MODEL": "gemini-flash-latest"},
            clear=True,
        ):
            model, source = gemini_service._resolve_organize_model({})
            self.assertEqual(model, "gemini-flash-latest")
            self.assertEqual(source, "env")

        # Deprecated legacy GEMINI_ORGANIZE_MODEL auto-substitutes gemini-flash-latest with warning
        with patch.dict("os.environ", {"GEMINI_ORGANIZE_MODEL": "gemini-2.0-flash"}, clear=True):
            with self.assertLogs(level="WARNING") as cm:
                model, source = gemini_service._resolve_organize_model({})
            self.assertEqual(model, "gemini-flash-latest")
            self.assertEqual(source, "env")
            self.assertTrue(any("GEMINI_ORGANIZE_MODEL" in msg and "gemini-2.0-flash" in msg for msg in cm.output))

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_uses_interactions_api_with_store_false_and_minimal_thinking(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._genre_interaction(
            [
                {"id": 0, "p": "Indie Rock", "s": []},
                {"id": 1, "p": None, "s": []},
            ]
        )

        tracks = [
            {"artist": "A", "title": "1", "isrc": "isrc1"},
            {"artist": "B", "title": "2", "isrc": "isrc2"},
        ]

        results = gemini_service.classify_tracks_genres("test-key", tracks)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["artist"], "A")
        self.assertEqual(results[0]["title"], "1")
        self.assertEqual(results[0]["isrc"], "isrc1")
        self.assertEqual(results[0]["primary_genre"], "Indie Rock")
        self.assertEqual(results[0]["genre"], "Indie Rock")
        self.assertEqual(results[1]["artist"], "B")
        self.assertEqual(results[1]["isrc"], "isrc2")
        self.assertIsNone(results[1]["genre"])

        mock_client.models.generate_content.assert_not_called()
        mock_client.interactions.create.assert_called_once()
        _, kwargs = mock_client.interactions.create.call_args
        self.assertIs(kwargs["store"], False)
        # gemini-flash-latest currently tracks gemini-3.8-flash and proactively uses 'low'
        # to avoid a wasted HTTP 400 round-trip on every batch.
        self.assertEqual(kwargs["generation_config"], {"thinking_level": "low"})
        self.assertNotIn("temperature", kwargs["generation_config"])
        # Compact numbered prompt must not echo ISRCs to Gemini (Principle VI & VIII).
        self.assertIn("0: A - 1", kwargs["input"])
        self.assertIn("1: B - 2", kwargs["input"])
        self.assertNotIn("isrc1", kwargs["input"])
        self.assertNotIn("isrc2", kwargs["input"])
        self.assertEqual(
            kwargs["response_format"]["schema"],
            gemini_service.GenreClassificationList.model_json_schema(),
        )

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_maps_out_of_order_and_missing_ids_safely(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        # Returned out-of-order, with track 1 omitted and an invalid id=99 ignored
        mock_client.interactions.create.return_value = self._genre_interaction(
            [
                {"id": 2, "p": "Modal Jazz", "s": ["Cool Jazz"]},
                {"id": 99, "p": "Bogus", "s": []},
                {"id": 0, "p": "Math Rock", "s": ["Dance-Punk"]},
            ]
        )

        tracks = [
            {"artist": "Foals", "title": "Tron", "isrc": "ISRC0"},
            {"artist": "Unknown", "title": "Skipped", "isrc": "ISRC1"},
            {"artist": "Miles Davis", "title": "So What", "isrc": "ISRC2"},
        ]

        results = gemini_service.classify_tracks_genres("test-key", tracks)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["artist"], "Foals")
        self.assertEqual(results[0]["primary_genre"], "Math Rock")
        self.assertEqual(results[1]["artist"], "Unknown")
        self.assertIsNone(results[1]["primary_genre"])
        self.assertEqual(results[1]["sub_genres"], [])
        self.assertEqual(results[2]["artist"], "Miles Davis")
        self.assertEqual(results[2]["primary_genre"], "Modal Jazz")

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_proactively_uses_low_thinking_for_non_minimal_models(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._genre_interaction(
            [{"id": 0, "p": "Synthpop", "s": ["Electropop"]}]
        )

        with patch.dict("os.environ", {"GEMINI_MODEL": "gemini-3.8-flash"}, clear=True):
            results = gemini_service.classify_tracks_genres("test-key", [{"artist": "A", "title": "1"}])

        self.assertEqual(results[0]["primary_genre"], "Synthpop")
        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["generation_config"], {"thinking_level": "low"})

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_uses_minimal_thinking_for_flash_lite_models(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._genre_interaction(
            [{"id": 0, "p": "Synthpop", "s": ["Electropop"]}]
        )

        with patch.dict("os.environ", {"GEMINI_MODEL": "gemini-3.5-flash-lite"}, clear=True):
            results = gemini_service.classify_tracks_genres("test-key", [{"artist": "A", "title": "1"}])

        self.assertEqual(results[0]["primary_genre"], "Synthpop")
        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["generation_config"], {"thinking_level": "minimal"})

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_reactively_downgrades_minimal_to_low_on_400(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        bad_thinking_err = self._FakeInteractionsStatusError(
            "Invalid argument: thinking_level 'minimal' is not supported for this model",
            status_code=400,
        )
        ok_interaction = self._genre_interaction(
            [{"id": 0, "p": "Math Rock", "s": ["Dance-Punk"]}]
        )
        mock_client.interactions.create.side_effect = [bad_thinking_err, ok_interaction]

        with patch.dict("os.environ", {"GEMINI_MODEL": "gemini-custom-flash"}, clear=True):
            results = gemini_service.classify_tracks_genres("test-key", [{"artist": "Foals", "title": "Tron"}])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["primary_genre"], "Math Rock")
        self.assertEqual(mock_client.interactions.create.call_count, 2)
        first_kwargs = mock_client.interactions.create.call_args_list[0].kwargs
        second_kwargs = mock_client.interactions.create.call_args_list[1].kwargs
        self.assertEqual(first_kwargs["generation_config"], {"thinking_level": "minimal"})
        self.assertEqual(second_kwargs["generation_config"], {"thinking_level": "low"})

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_accuracy_evaluation_protocol(self, mock_client_class, _mock_dotenv):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        sample_tracks = [
            {"artist": "Miles Davis", "title": "Teardrop", "isrc": "1", "expected_genres": {"Electronic", "Trip Hop"}},
            {"artist": "Metallica", "title": "Enter Sandman", "isrc": "2", "expected_genres": {"Metal", "Rock"}},
            {"artist": "Beethoven", "title": "So What", "isrc": "3", "expected_genres": {"Jazz", "Classical"}},
        ]

        mock_client.interactions.create.return_value = self._genre_interaction(
            [
                {"id": 0, "p": "Electronic", "s": []},
                {"id": 1, "p": "Metal", "s": []},
                {"id": 2, "p": "Classical", "s": []},
            ]
        )

        results = gemini_service.classify_tracks_genres("test-key", sample_tracks)

        correct_count = 0
        for track, result in zip(sample_tracks, results):
            expected = track["expected_genres"]
            returned = {result["genre"]} if result.get("genre") else set()
            if expected.intersection(returned):
                correct_count += 1

        accuracy = correct_count / len(sample_tracks)
        self.assertGreaterEqual(accuracy, 0.90)

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_multi_tier_sub_genres_capped_at_three(self, mock_client_class, _mock_dotenv):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._genre_interaction(
            [
                {
                    "id": 0,
                    "p": "Math Rock",
                    "s": ["Dance-Punk", "Post-Punk Revival", "Art Punk", "Extra Ignored"],
                }
            ]
        )

        tracks = [{"artist": "Foals", "title": "Tron", "isrc": "GBAHT0900329"}]
        results = gemini_service.classify_tracks_genres("test-key", tracks)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["artist"], "Foals")
        self.assertEqual(results[0]["title"], "Tron")
        self.assertEqual(results[0]["isrc"], "GBAHT0900329")
        self.assertEqual(results[0]["primary_genre"], "Math Rock")
        self.assertEqual(results[0]["genre"], "Math Rock")
        self.assertEqual(results[0]["sub_genres"], ["Dance-Punk", "Post-Punk Revival", "Art Punk"])

    def test_genre_classification_result_model(self):
        item = gemini_service.GenreClassificationResult(
            artist="Foals",
            title="Tron",
            primary_genre="Math Rock",
            sub_genres=["Dance-Punk", "Post-Punk Revival"],
        )
        dump = item.model_dump()
        self.assertEqual(dump["primary_genre"], "Math Rock")
        self.assertEqual(dump["sub_genres"], ["Dance-Punk", "Post-Punk Revival"])

    # ------------------------------------------------------------------
    # US4: Flex Tier, Timeout, Fallback & Error Categorization Tests
    # ------------------------------------------------------------------

    def test_resolve_service_tier_cli_flag_takes_precedence(self):
        tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=True, dotenv_config={})
        self.assertEqual(tier, "flex")
        self.assertEqual(source, "cli")
        self.assertEqual(timeout, 900_000)

        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "flex"}, clear=True):
            tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=False, dotenv_config={})
            self.assertEqual(tier, "standard")
            self.assertEqual(source, "cli")
            self.assertEqual(timeout, 120_000)

        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "standard"}, clear=True):
            tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=True, dotenv_config={})
            self.assertEqual(tier, "flex")
            self.assertEqual(source, "cli")
            self.assertEqual(timeout, 900_000)

    def test_resolve_service_tier_environment_variable(self):
        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "flex"}, clear=True):
            tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=None, dotenv_config={})
            self.assertEqual(tier, "flex")
            self.assertEqual(source, "env")
            self.assertEqual(timeout, 900_000)

        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "standard"}, clear=True):
            tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=None, dotenv_config={})
            self.assertEqual(tier, "standard")
            self.assertEqual(source, "env")
            self.assertEqual(timeout, 120_000)

    def test_resolve_service_tier_case_insensitivity_and_whitespace(self):
        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "  FLEX  "}, clear=True):
            tier, source, _ = gemini_service._resolve_service_tier(cli_flex=None, dotenv_config={})
            self.assertEqual(tier, "flex")
            self.assertEqual(source, "env")

        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "  Standard\t"}, clear=True):
            tier, source, _ = gemini_service._resolve_service_tier(cli_flex=None, dotenv_config={})
            self.assertEqual(tier, "standard")
            self.assertEqual(source, "env")

    def test_resolve_service_tier_dotenv_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            tier, source, timeout = gemini_service._resolve_service_tier(
                cli_flex=None,
                dotenv_config={"GEMINI_SERVICE_TIER": "flex"},
            )
            self.assertEqual(tier, "flex")
            self.assertEqual(source, "dotenv")
            self.assertEqual(timeout, 900_000)

    def test_resolve_service_tier_unrecognized_value_falls_back(self):
        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER": "invalid_tier"}, clear=True):
            with self.assertLogs(level="WARNING") as cm:
                tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=None, dotenv_config={})
            self.assertEqual(tier, "standard")
            self.assertEqual(source, "default")
            self.assertEqual(timeout, 120_000)
            self.assertTrue(any("Unrecognized GEMINI_SERVICE_TIER 'invalid_tier'" in msg for msg in cm.output))

    def test_resolve_service_tier_default(self):
        with patch.dict("os.environ", {}, clear=True):
            tier, source, timeout = gemini_service._resolve_service_tier(cli_flex=None, dotenv_config={})
            self.assertEqual(tier, "standard")
            self.assertEqual(source, "default")
            self.assertEqual(timeout, 120_000)

    def test_resolve_flex_timeout_seconds(self):
        with patch.dict("os.environ", {"GEMINI_FLEX_TIMEOUT_SECONDS": "600"}, clear=True):
            timeout_s = gemini_service._resolve_flex_timeout_seconds({})
            self.assertEqual(timeout_s, 600)
            _, _, timeout_ms = gemini_service._resolve_service_tier(cli_flex=True, dotenv_config={})
            self.assertEqual(timeout_ms, 600_000)

        with patch.dict("os.environ", {"GEMINI_FLEX_TIMEOUT_SECONDS": "invalid"}, clear=True):
            with self.assertLogs(level="WARNING") as cm:
                timeout_s = gemini_service._resolve_flex_timeout_seconds({})
            self.assertEqual(timeout_s, 900)
            self.assertTrue(any("Invalid GEMINI_FLEX_TIMEOUT_SECONDS 'invalid'" in msg for msg in cm.output))

        with patch.dict("os.environ", {"GEMINI_FLEX_TIMEOUT_SECONDS": "-10"}, clear=True):
            with self.assertLogs(level="WARNING") as cm:
                timeout_s = gemini_service._resolve_flex_timeout_seconds({})
            self.assertEqual(timeout_s, 900)
            self.assertTrue(any("Invalid GEMINI_FLEX_TIMEOUT_SECONDS '-10'" in msg for msg in cm.output))

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_get_recommendations_configures_flex_tier_and_client_timeout(self, mock_client_class, _mock_dotenv):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._rec_interaction(
            [{"artist": "Artist A", "title": "Track A"}]
        )

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        result = gemini_service.get_recommendations("test-key", [seed_track], 1, flex=True)

        self.assertEqual(len(result), 1)
        mock_client_class.assert_called_once_with(
            api_key="test-key",
            http_options={"timeout": 900_000, "api_version": "v1beta"},
        )
        mock_client.interactions.create.assert_called_once()
        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["service_tier"], "flex")
        self.assertIs(kwargs["store"], False)

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_configures_flex_tier_and_client_timeout(self, mock_client_class, _mock_dotenv):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._genre_interaction(
            [{"id": 0, "p": "Indie Rock", "s": []}]
        )

        tracks = [{"artist": "A", "title": "1"}]
        results = gemini_service.classify_tracks_genres("test-key", tracks, flex=True)

        self.assertEqual(len(results), 1)
        mock_client_class.assert_called_once_with(
            api_key="test-key",
            http_options={"timeout": 900_000, "api_version": "v1beta"},
        )
        mock_client.interactions.create.assert_called_once()
        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["service_tier"], "flex")
        self.assertIs(kwargs["store"], False)

    @patch("src.services.gemini_service.genai.Client")
    def test_get_recommendations_uses_dotenv_flex_when_cli_none(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._rec_interaction(
            [{"artist": "Artist A", "title": "Track A"}]
        )

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        with patch("src.services.gemini_service._read_dotenv_values", return_value={"GEMINI_SERVICE_TIER": "flex"}):
            with patch.dict("os.environ", {}, clear=True):
                gemini_service.get_recommendations("test-key", [seed_track], 1, flex=None)

        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["service_tier"], "flex")

    @patch("src.services.gemini_service.genai.Client")
    def test_get_recommendations_cli_no_flex_overrides_dotenv_flex(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._rec_interaction(
            [{"artist": "Artist A", "title": "Track A"}]
        )

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        with patch("src.services.gemini_service._read_dotenv_values", return_value={"GEMINI_SERVICE_TIER": "flex"}):
            with patch.dict("os.environ", {}, clear=True):
                gemini_service.get_recommendations("test-key", [seed_track], 1, flex=False)

        _, kwargs = mock_client.interactions.create.call_args
        self.assertEqual(kwargs["service_tier"], "standard")

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_flex_timeout_raises_actionable_error_for_timeout_and_api_timeout_error(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        for exc in (TimeoutError("Deadline exceeded"), self._FakeAPITimeoutError("Request timed out")):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.interactions.create.side_effect = exc

            seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
            with self.assertRaises(ValueError) as ctx:
                gemini_service.get_recommendations("test-key", [seed_track], 1, flex=True)

            err_msg = str(ctx.exception)
            self.assertIn("category='flex-timeout'", err_msg)
            self.assertIn("--no-flex", err_msg)

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_auth_and_permission_errors_fail_immediately_without_retry_or_fallback(
        self,
        mock_client_class,
        _mock_dotenv,
    ):
        for status_code, expected_cat in ((401, "auth"), (403, "permission")):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.interactions.create.side_effect = self._FakeInteractionsStatusError(
                f"HTTP {status_code} failure", status_code=status_code
            )

            seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
            with patch.dict("os.environ", {"GEMINI_FALLBACK_MODEL": "gemini-3.5-flash-lite"}, clear=True):
                with self.assertRaises(ValueError) as ctx:
                    gemini_service.get_recommendations("test-key", [seed_track], 1)

            self.assertEqual(mock_client.interactions.create.call_count, 1)
            self.assertIn(f"category='{expected_cat}'", str(ctx.exception))

    @patch("time.sleep")
    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_flex_capacity_exhaustion_fails_fast_without_standard_fallback(
        self,
        mock_client_class,
        _mock_dotenv,
        _mock_sleep,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.side_effect = self._FakeInteractionsStatusError(
            "Resource Exhausted", status_code=429
        )

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        with self.assertRaises(ValueError) as ctx:
            gemini_service.get_recommendations("test-key", [seed_track], 1, flex=True)

        expected_calls = gemini_service.DEFAULT_FLEX_RETRY_LIMIT + 1
        self.assertEqual(mock_client.interactions.create.call_count, expected_calls)
        for call in mock_client.interactions.create.call_args_list:
            self.assertEqual(call.kwargs["service_tier"], "flex")

        err_msg = str(ctx.exception)
        self.assertIn("category='flex-capacity'", err_msg)
        self.assertIn("temporarily unavailable due to demand", err_msg)
        self.assertIn("--no-flex", err_msg)

    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_structured_service_tier_info_logging(self, mock_client_class, _mock_dotenv):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.interactions.create.return_value = self._rec_interaction(
            [{"artist": "Artist A", "title": "Track A"}]
        )

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()

        with self.assertLogs("root", level="INFO") as log_capture:
            gemini_service.get_recommendations("test-key", [seed_track], 1, flex=True)

        log_output = "\n".join(log_capture.output)
        self.assertIn("Gemini service tier resolution: tier='flex' source='cli' timeout=900000ms", log_output)
        self.assertIn("Gemini recommendations retrieved successfully (tier='flex')", log_output)

    @patch("time.sleep")
    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_flex_503_server_error_classified_as_flex_capacity(self, mock_client_class, _mock_dotenv, _mock_sleep):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        server_error = self._FakeInteractionsStatusError(
            "This model is currently experiencing high demand. Spikes in demand are usually temporary.",
            status_code=503,
        )
        mock_client.interactions.create.side_effect = server_error

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        with self.assertRaises(ValueError) as ctx:
            gemini_service.get_recommendations("test-key", [seed_track], 1, flex=True)

        expected_calls = gemini_service.DEFAULT_FLEX_RETRY_LIMIT + 1
        self.assertEqual(mock_client.interactions.create.call_count, expected_calls)
        err_msg = str(ctx.exception)
        self.assertIn("category='flex-capacity'", err_msg)
        self.assertIn("temporarily unavailable due to demand", err_msg)
        self.assertIn("--no-flex", err_msg)

    def test_flex_retry_policy_resolution(self):
        self.assertEqual(gemini_service._resolve_retry_limit("standard"), 1)
        self.assertEqual(gemini_service._resolve_retry_limit("flex"), 5)

        with patch.dict("os.environ", {"GEMINI_FLEX_MAX_RETRIES": "8"}, clear=True):
            self.assertEqual(gemini_service._resolve_retry_limit("flex"), 8)

        self.assertEqual(gemini_service._resolve_retry_limit("flex", {"GEMINI_FLEX_MAX_RETRIES": "3"}), 3)

        with patch.dict("os.environ", {"GEMINI_FLEX_MAX_RETRIES": "invalid"}, clear=True):
            self.assertEqual(gemini_service._resolve_retry_limit("flex"), 5)

    def test_get_retry_backoff_schedule(self):
        self.assertEqual(gemini_service._get_retry_backoff(1, "standard"), 2.0)
        self.assertEqual(gemini_service._get_retry_backoff(2, "standard"), 2.0)

        self.assertEqual(gemini_service._get_retry_backoff(1, "flex"), 5.0)
        self.assertEqual(gemini_service._get_retry_backoff(2, "flex"), 10.0)
        self.assertEqual(gemini_service._get_retry_backoff(3, "flex"), 20.0)
        self.assertEqual(gemini_service._get_retry_backoff(4, "flex"), 30.0)
        self.assertEqual(gemini_service._get_retry_backoff(5, "flex"), 60.0)
        self.assertEqual(gemini_service._get_retry_backoff(6, "flex"), 60.0)

    @patch("time.sleep")
    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_flex_retry_succeeds_after_transient_503(self, mock_client_class, _mock_dotenv, mock_sleep):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        server_error = self._FakeInteractionsStatusError("High demand spike", status_code=503)
        usable_response = self._rec_interaction([{"artist": "Artist A", "title": "Track A"}])
        mock_client.interactions.create.side_effect = [server_error, usable_response]

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        with self.assertLogs("root", level="INFO") as log_capture:
            recs = gemini_service.get_recommendations("test-key", [seed_track], 1, flex=True)

        self.assertEqual(len(recs), 1)
        self.assertEqual(mock_client.interactions.create.call_count, 2)
        mock_sleep.assert_called_once_with(5.0)
        log_text = "\n".join(log_capture.output)
        self.assertIn("Gemini flex capacity busy (HTTP 503 demand spike). Waiting 5s", log_text)

    @patch("time.sleep")
    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_flex_retry_succeeds(self, mock_client_class, _mock_dotenv, mock_sleep):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        server_error = self._FakeInteractionsStatusError("High demand spike", status_code=503)
        mock_response = self._genre_interaction(
            [{"id": 0, "p": "Post-Punk", "s": []}]
        )
        mock_client.interactions.create.side_effect = [server_error, mock_response]

        tracks = [{"artist": "Artist A", "title": "Song 1"}]
        with self.assertLogs("root", level="INFO") as log_capture:
            results = gemini_service.classify_tracks_genres("test-key", tracks, flex=True)

        self.assertEqual(len(results), 1)
        self.assertEqual(mock_client.interactions.create.call_count, 2)
        mock_sleep.assert_called_once_with(5.0)
        log_text = "\n".join(log_capture.output)
        self.assertIn("Gemini flex capacity busy (HTTP 503 demand spike). Waiting 5s", log_text)

    def test_resolve_flex_fallback_standard_cli_overrides(self):
        with patch.dict("os.environ", {"GEMINI_FLEX_FALLBACK_STANDARD": "false"}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=True, dotenv_config={})
            self.assertTrue(fallback)
            self.assertEqual(source, "cli")

        with patch.dict("os.environ", {"GEMINI_FLEX_FALLBACK_STANDARD": "true"}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=False, dotenv_config={})
            self.assertFalse(fallback)
            self.assertEqual(source, "cli")

    def test_resolve_flex_fallback_standard_env_boolean_parsing(self):
        for val in ["true", "TRUE", "True", "1", "yes", "YES", "  true  "]:
            with patch.dict("os.environ", {"GEMINI_FLEX_FALLBACK_STANDARD": val}, clear=True):
                fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
                self.assertTrue(fallback, f"Expected {val} to resolve to True")
                self.assertEqual(source, "env")

        for val in ["false", "FALSE", "False", "0", "no", "NO", "  false  "]:
            with patch.dict("os.environ", {"GEMINI_FLEX_FALLBACK_STANDARD": val}, clear=True):
                fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
                self.assertFalse(fallback, f"Expected {val} to resolve to False")
                self.assertEqual(source, "env")

    def test_resolve_flex_fallback_standard_dotenv_and_default(self):
        with patch.dict("os.environ", {}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(
                cli_fallback=None,
                dotenv_config={"GEMINI_FLEX_FALLBACK_STANDARD": "true"},
            )
            self.assertTrue(fallback)
            self.assertEqual(source, "dotenv")

        with patch.dict("os.environ", {}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
            self.assertFalse(fallback)
            self.assertEqual(source, "default")

    def test_resolve_flex_fallback_standard_invalid_value_warning(self):
        with patch.dict("os.environ", {"GEMINI_FLEX_FALLBACK_STANDARD": "invalid_bool"}, clear=True):
            with self.assertLogs(level="WARNING") as cm:
                fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
            self.assertFalse(fallback)
            self.assertEqual(source, "default")
            self.assertTrue(any("Invalid GEMINI_FLEX_FALLBACK_STANDARD 'invalid_bool'" in msg for msg in cm.output))

    def test_resolve_flex_fallback_standard_service_tier_fallback_alias(self):
        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER_FALLBACK": "standard"}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
            self.assertTrue(fallback)
            self.assertEqual(source, "env")

        with patch.dict("os.environ", {"GEMINI_SERVICE_TIER_FALLBACK": "true"}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
            self.assertTrue(fallback)
            self.assertEqual(source, "env")

        with patch.dict("os.environ", {}, clear=True):
            fallback, source = gemini_service._resolve_flex_fallback_standard(
                cli_fallback=None,
                dotenv_config={"GEMINI_SERVICE_TIER_FALLBACK": "standard"},
            )
            self.assertTrue(fallback)
            self.assertEqual(source, "dotenv")

        with patch.dict(
            "os.environ",
            {"GEMINI_FLEX_FALLBACK_STANDARD": "false", "GEMINI_SERVICE_TIER_FALLBACK": "standard"},
            clear=True,
        ):
            fallback, source = gemini_service._resolve_flex_fallback_standard(cli_fallback=None, dotenv_config={})
            self.assertFalse(fallback)
            self.assertEqual(source, "env")

    @patch("time.sleep")
    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_get_recommendations_falls_back_to_standard_tier_when_enabled(
        self,
        mock_client_class,
        _mock_dotenv,
        _mock_sleep,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        server_error = self._FakeInteractionsStatusError("High demand spike", status_code=503)
        standard_response = self._rec_interaction([{"artist": "Standard Artist", "title": "Standard Track"}])
        mock_client.interactions.create.side_effect = [server_error] * 6 + [standard_response]

        seed_track = type("Seed", (), {"artist": type("A", (), {"name": "Artist"})(), "name": "Song"})()
        on_fallback_cb = MagicMock()

        with self.assertLogs("root", level="WARNING") as log_capture:
            results = gemini_service.get_recommendations(
                "test-key",
                [seed_track],
                1,
                flex=True,
                flex_fallback_standard=True,
                on_fallback=on_fallback_cb,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["artist"], "Standard Artist")
        self.assertEqual(mock_client.interactions.create.call_count, 7)
        on_fallback_cb.assert_called_once()

        # Verify initial flex client used 900s timeout and fallback standard client used 120s timeout.
        self.assertEqual(mock_client_class.call_count, 2)
        self.assertEqual(
            mock_client_class.call_args_list[0].kwargs["http_options"],
            {"timeout": 900_000, "api_version": "v1beta"},
        )
        self.assertEqual(
            mock_client_class.call_args_list[1].kwargs["http_options"],
            {"timeout": 120_000, "api_version": "v1beta"},
        )

        _, last_kwargs = mock_client.interactions.create.call_args_list[-1]
        self.assertEqual(last_kwargs["service_tier"], "standard")

        warning_logs = "\n".join(log_capture.output)
        self.assertIn("Falling back to standard tier as configured", warning_logs)

    @patch("time.sleep")
    @patch("src.services.gemini_service._read_dotenv_values", return_value={})
    @patch("src.services.gemini_service.genai.Client")
    def test_classify_tracks_genres_falls_back_to_standard_tier_when_enabled(
        self,
        mock_client_class,
        _mock_dotenv,
        _mock_sleep,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        server_error = self._FakeInteractionsStatusError("High demand spike", status_code=503)
        standard_response = self._genre_interaction(
            [{"id": 0, "p": "Synthpop", "s": []}]
        )
        mock_client.interactions.create.side_effect = [server_error] * 6 + [standard_response]

        tracks = [{"artist": "Artist A", "title": "Song 1"}]
        on_fallback_cb = MagicMock()

        with self.assertLogs("root", level="WARNING") as log_capture:
            results = gemini_service.classify_tracks_genres(
                "test-key",
                tracks,
                flex=True,
                flex_fallback_standard=True,
                on_fallback=on_fallback_cb,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["primary_genre"], "Synthpop")
        self.assertEqual(mock_client.interactions.create.call_count, 7)
        on_fallback_cb.assert_called_once()
        self.assertEqual(
            mock_client_class.call_args_list[0].kwargs["http_options"],
            {"timeout": 900_000, "api_version": "v1beta"},
        )
        self.assertEqual(
            mock_client_class.call_args_list[1].kwargs["http_options"],
            {"timeout": 120_000, "api_version": "v1beta"},
        )

        _, last_kwargs = mock_client.interactions.create.call_args_list[-1]
        self.assertEqual(last_kwargs["service_tier"], "standard")
        warning_logs = "\n".join(log_capture.output)
        self.assertIn("Falling back to standard tier as configured", warning_logs)

    def test_flex_heartbeat_emits_logs_for_flex_tier(self):
        with self.assertLogs("root", level="INFO") as log_capture:
            with gemini_service._flex_heartbeat("flex", timeout_ms=60_000, interval_seconds=0.03):
                threading.Event().wait(0.08)

        logs = "\n".join(log_capture.output)
        self.assertIn("Waiting for Gemini Flex opportunistic capacity...", logs)
        self.assertIn("timeout: 60s", logs)

    def test_flex_heartbeat_noop_for_standard_tier(self):
        with self.assertLogs("root", level="INFO") as log_capture:
            gemini_service.logging.info("Baseline sentinel")
            with gemini_service._flex_heartbeat("standard", timeout_ms=60_000, interval_seconds=0.03):
                threading.Event().wait(0.08)

        logs = "\n".join(log_capture.output)
        self.assertNotIn("Waiting for Gemini Flex opportunistic capacity...", logs)


if __name__ == "__main__":
    unittest.main()
