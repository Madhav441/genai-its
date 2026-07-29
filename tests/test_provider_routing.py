"""Automated tests for DP5 configuration-driven provider routing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "1.3_models"

if str(MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(MODELS_DIR))

from llm_provider import get_llm, get_routing_summary


class ProviderRoutingTests(unittest.TestCase):
    def test_routing_summary_loads_from_yaml(self):
        summary = get_routing_summary()

        self.assertEqual(summary["active_provider"], "ollama")
        self.assertEqual(summary["fallback_provider"], "ollama")
        self.assertTrue(summary["allow_fallback"])

    def test_all_required_providers_are_configured(self):
        summary = get_routing_summary()

        enabled = set(summary["enabled_providers"])

        self.assertIn("ollama", enabled)
        self.assertIn("groq", enabled)
        self.assertIn("openai", enabled)

    def test_active_provider_is_enabled(self):
        summary = get_routing_summary()

        self.assertIn(
            summary["active_provider"],
            summary["enabled_providers"],
        )

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            get_llm(provider="invalid-provider")


if __name__ == "__main__":
    unittest.main()