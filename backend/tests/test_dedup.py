from scrapers.dedup import DeduplicationEngine
from run_monitors import remove_dangling_free_alternatives


def test_seed_mode_preserves_same_domain_tools():
    dedup = DeduplicationEngine()

    chatgpt = {
        "id": "chatgpt",
        "name": "ChatGPT",
        "website": "https://openai.com/chatgpt",
        "categories": ["chatbots"],
    }
    whisper = {
        "id": "whisper-openai",
        "name": "Whisper",
        "website": "https://openai.com/research/whisper",
        "categories": ["speech-to-text"],
    }

    dedup.add(chatgpt, check_duplicates=False)
    dedup.add(whisper, check_duplicates=False)

    assert [tool["id"] for tool in dedup.get_unique()] == ["chatgpt", "whisper-openai"]


def test_remove_dangling_free_alternatives_keeps_only_existing_ids():
    tools = [
        {
            "id": "elevenlabs",
            "free_alternatives": ["openai-tts", "missing-tool"],
        },
        {"id": "openai-tts", "free_alternatives": []},
    ]

    removed = remove_dangling_free_alternatives(tools)

    assert removed == 1
    assert tools[0]["free_alternatives"] == ["openai-tts"]
