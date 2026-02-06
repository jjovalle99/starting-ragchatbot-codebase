from config import Config


class TestConfig:
    def test_default_values(self):
        cfg = Config(OPENAI_API_KEY="test-key")
        assert cfg.OPENAI_MODEL == "gpt-4o"
        assert cfg.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert cfg.CHUNK_SIZE == 800
        assert cfg.CHUNK_OVERLAP == 100
        assert cfg.MAX_RESULTS == 5
        assert cfg.MAX_HISTORY == 2
        assert cfg.CHROMA_PATH == "./chroma_db"

    def test_custom_overrides(self):
        cfg = Config(
            OPENAI_API_KEY="my-key",
            OPENAI_MODEL="gpt-3.5-turbo",
            CHUNK_SIZE=400,
            CHROMA_PATH="/tmp/test_db",
        )
        assert cfg.OPENAI_API_KEY == "my-key"
        assert cfg.OPENAI_MODEL == "gpt-3.5-turbo"
        assert cfg.CHUNK_SIZE == 400
        assert cfg.CHROMA_PATH == "/tmp/test_db"
