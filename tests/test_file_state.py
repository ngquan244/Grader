import os
from concurrent.futures import ThreadPoolExecutor

os.environ["DEBUG"] = "false"

from backend.modules.document_rag.topic_storage import TopicStorage
from backend.utils.file_state import locked_json_state, read_json_file


def test_locked_json_state_round_trip(tmp_path):
    state_file = tmp_path / "state.json"

    with locked_json_state(state_file, dict) as state:
        state["alpha"] = {"count": 1}

    loaded = read_json_file(state_file, dict)
    assert loaded == {"alpha": {"count": 1}}


def test_locked_json_state_serializes_thread_updates(tmp_path):
    state_file = tmp_path / "counter.json"

    def _increment():
        for _ in range(25):
            with locked_json_state(state_file, dict) as state:
                state["count"] = int(state.get("count", 0)) + 1

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_increment) for _ in range(4)]
        for future in futures:
            future.result()

    loaded = read_json_file(state_file, dict)
    assert loaded["count"] == 100


def test_topic_storage_scopes_same_hash_by_user(tmp_path):
    storage = TopicStorage(storage_dir=str(tmp_path))
    topics_a = [{"name": "Vectors", "description": ""}]
    topics_b = [{"name": "Matrices", "description": ""}]

    storage.save_topics("same-hash", "shared.pdf", topics_a, user_id="user-a")
    storage.save_topics("same-hash", "shared.pdf", topics_b, user_id="user-b")

    assert storage.get_topics("same-hash", user_id="user-a") == topics_a
    assert storage.get_topics("same-hash", user_id="user-b") == topics_b
    assert storage.get_topics_by_filename("shared.pdf", user_id="user-a") == topics_a
    assert storage.get_topics_by_filename("shared.pdf", user_id="user-b") == topics_b

    storage.remove_document("same-hash", user_id="user-a")

    assert storage.get_topics("same-hash", user_id="user-a") is None
    assert storage.get_topics("same-hash", user_id="user-b") == topics_b
