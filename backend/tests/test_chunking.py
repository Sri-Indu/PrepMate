from app.services.chunking import chunk_text


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_text("   \n\t  ") == []


def test_short_text_is_a_single_chunk() -> None:
    text = "Java SQL React"
    assert chunk_text(text, chunk_size=400, overlap=80) == [text]


def test_long_text_is_split_with_overlap() -> None:
    words = [f"word{i:02d}" for i in range(80)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=80, overlap=20)

    assert len(chunks) >= 3
    joined = " ".join(chunks)
    assert "word00" in chunks[0]
    assert "word79" in chunks[-1]
    # Overlap means some tokens appear in more than one chunk.
    first_last_word = chunks[0].split()[-1]
    assert first_last_word in chunks[1]
    assert len(joined) > len(text)
