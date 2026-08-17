import unittest

from backend.agents.sherpa_agent import sherpa_app
from backend.compaction import (
    COMPACTION_EVENT_RETENTION_SIZE,
    COMPACTION_TOKEN_LIMIT,
)


class CompactionTests(unittest.TestCase):
    def test_sherpa_compacts_at_requested_context_threshold(self) -> None:
        config = sherpa_app.events_compaction_config

        self.assertIsNotNone(config)
        self.assertEqual(config.token_threshold, COMPACTION_TOKEN_LIMIT)
        self.assertEqual(config.token_threshold, 300_000)
        self.assertEqual(
            config.event_retention_size,
            COMPACTION_EVENT_RETENTION_SIZE,
        )
        self.assertGreater(config.event_retention_size, 0)
