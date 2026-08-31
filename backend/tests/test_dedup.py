from scrapers.dedup import DeduplicationEngine


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
