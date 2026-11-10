import os
import unittest
from unittest.mock import patch

# Importing the clinic connection validates MYSQL_* settings. These placeholders
# allow this isolated test to import the module without making a DB connection.
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_DATABASE", "test")

from clinic_assistant.database import connection as clinic_connection
from mcp_layer.database import connection as mcp_connection
from mcp_layer.database.initialize import initialize_token_usage_table
from mcp_layer.database.models import TokenUsage


class TokenUsageDatabaseTests(unittest.TestCase):
    def test_mcp_uses_shared_clinic_engine_and_session_factory(self):
        self.assertIs(mcp_connection.engine, clinic_connection.engine)
        self.assertIs(mcp_connection.SessionLocal, clinic_connection.SessionLocal)

    def test_initialization_creates_only_token_usage_idempotently(self):
        with patch.object(TokenUsage.__table__, "create") as create:
            initialize_token_usage_table()
            initialize_token_usage_table()

        self.assertEqual(create.call_count, 2)
        for call in create.call_args_list:
            self.assertIs(call.kwargs["bind"], clinic_connection.engine)
            self.assertTrue(call.kwargs["checkfirst"])


if __name__ == "__main__":
    unittest.main()
