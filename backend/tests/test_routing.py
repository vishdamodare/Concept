import os
import unittest
from unittest.mock import AsyncMock, patch
from llm.chat import LlmChat

class TestLlmRouting(unittest.TestCase):
    def setUp(self):
        # Backup environment variables
        self.env_backup = {}
        for key in ["LITELLM_API_BASE", "OPENAI_API_BASE", "GEMINI_API_KEY", "GOOGLE_API_KEY", "LLM_MODEL"]:
            self.env_backup[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]

    def tearDown(self):
        # Restore environment variables
        for key, value in self.env_backup.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

    def test_routing_with_google_key(self):
        # GIVEN a Google API Key is set
        os.environ["GOOGLE_API_KEY"] = "test-google-key"
        
        # WHEN resolving API setup
        chat = LlmChat(api_key="", session_id="test", system_message="sys")
        chat.with_model("anthropic", "claude-sonnet-4-6")
        
        model_name, target_api_key = chat._get_api_setup()
        
        # THEN it should route directly to Gemini (mapping Claude to Gemini)
        self.assertEqual(model_name, "gemini/gemini-2.5-flash")
        self.assertEqual(target_api_key, "test-google-key")

    def test_routing_with_gemini_key_for_gemini_model(self):
        # GIVEN a Gemini API Key is set
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        
        # WHEN resolving API setup for a Gemini model
        chat = LlmChat(api_key="", session_id="test", system_message="sys")
        chat.with_model("gemini", "gemini-1.5-flash")
        
        model_name, target_api_key = chat._get_api_setup()
        
        # THEN it should route directly to Google Gemini using the specific model
        self.assertEqual(model_name, "gemini/gemini-1.5-flash")
        self.assertEqual(target_api_key, "test-gemini-key")

    def test_routing_model_name_prefix_normalization(self):
        # GIVEN a Gemini API Key is set
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        
        # WHEN the user sets LLM_MODEL without prefix (e.g. gemini-2.5-flash)
        chat = LlmChat(api_key="", session_id="test", system_message="sys")
        chat.with_model("gemini", "gemini-2.5-flash")
        
        model_name, target_api_key = chat._get_api_setup()
        
        # THEN model name should be normalized to start with "gemini/"
        self.assertEqual(model_name, "gemini/gemini-2.5-flash")
        self.assertEqual(target_api_key, "test-gemini-key")

    def test_routing_with_no_key_warning(self):
        # GIVEN no key is configured in the environment
        chat = LlmChat(api_key="", session_id="test", system_message="sys")
        
        model_name, target_api_key = chat._get_api_setup()
        
        # THEN target api key should be empty and model name should default to gemini-2.5-flash with prefix
        self.assertEqual(model_name, "gemini/gemini-2.5-flash")
        self.assertEqual(target_api_key, "")

class TestLlmRetry(unittest.IsolatedAsyncioTestCase):
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_on_rate_limit(self, mock_sleep):
        # GIVEN LlmChat instance with mock key
        chat = LlmChat(api_key="test-key", session_id="test", system_message="sys")
        
        # GIVEN a mock function that fails with a 429 Rate Limit error once, then succeeds
        mock_func = AsyncMock()
        mock_func.side_effect = [
            Exception("RateLimitError: 429 Quota Exceeded"),
            "success-response"
        ]
        
        # WHEN executing with retry
        res = await chat._execute_with_retry(mock_func)
        
        # THEN it should succeed after retrying once
        self.assertEqual(res, "success-response")
        self.assertEqual(mock_func.call_count, 2)
        mock_sleep.assert_called_once()
        
        # Verify the sleep was called with exponential backoff + jitter (should be around 2.X s)
        sleep_arg = mock_sleep.call_args[0][0]
        self.assertTrue(1.0 <= sleep_arg <= 4.0)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_fail_immediately_on_permanent_error(self, mock_sleep):
        # GIVEN LlmChat instance
        chat = LlmChat(api_key="test-key", session_id="test", system_message="sys")
        
        # GIVEN a mock function that fails with a 401 Unauthorized error
        mock_func = AsyncMock()
        mock_func.side_effect = Exception("APIKeyError: 401 Invalid API Key")
        
        # WHEN executing with retry
        with self.assertRaises(Exception) as ctx:
            await chat._execute_with_retry(mock_func)
            
        # THEN it should fail immediately without sleeping
        self.assertIn("401", str(ctx.exception))
        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()

if __name__ == "__main__":
    unittest.main()
