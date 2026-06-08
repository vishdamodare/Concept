import os
import unittest
from emergentintegrations.llm.chat import LlmChat

class TestLlmRouting(unittest.TestCase):
    def setUp(self):
        # Backup environment variables
        self.env_backup = {}
        for key in ["LITELLM_API_BASE", "OPENAI_API_BASE", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
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
        
        # WHEN resolving API setup for a Claude model
        chat = LlmChat(api_key="sk-emergent-key", session_id="test", system_message="sys")
        chat.with_model("anthropic", "claude-sonnet-4-6")
        
        api_base, model_name, use_direct_proxy, target_api_key = chat._get_api_setup()
        
        # THEN it should route directly to Gemini (no proxy, target key is Google key)
        self.assertIsNone(api_base)
        self.assertEqual(model_name, "gemini/gemini-2.0-flash")
        self.assertFalse(use_direct_proxy)
        self.assertEqual(target_api_key, "test-google-key")

    def test_routing_with_gemini_key_for_gemini_model(self):
        # GIVEN a Gemini API Key is set
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        
        # WHEN resolving API setup for a Gemini model
        chat = LlmChat(api_key="sk-emergent-key", session_id="test", system_message="sys")
        chat.with_model("gemini", "gemini-1.5-flash")
        
        api_base, model_name, use_direct_proxy, target_api_key = chat._get_api_setup()
        
        # THEN it should route directly to Google Gemini using the specific model
        self.assertIsNone(api_base)
        self.assertEqual(model_name, "gemini/gemini-1.5-flash")
        self.assertFalse(use_direct_proxy)
        self.assertEqual(target_api_key, "test-gemini-key")

    def test_routing_with_only_emergent_key(self):
        # GIVEN only the emergent key is set
        # (no GOOGLE_API_KEY or GEMINI_API_KEY)
        
        # WHEN resolving API setup for a Claude model
        chat = LlmChat(api_key="sk-emergent-key", session_id="test", system_message="sys")
        chat.with_model("anthropic", "claude-sonnet-4-6")
        
        api_base, model_name, use_direct_proxy, target_api_key = chat._get_api_setup()
        
        # THEN it should route via the default platform proxy
        self.assertEqual(api_base, "https://api.emergent.sh")
        self.assertEqual(model_name, "anthropic/claude-sonnet-4-6")
        self.assertTrue(use_direct_proxy)
        self.assertEqual(target_api_key, "sk-emergent-key")

if __name__ == "__main__":
    unittest.main()
