import hashlib

from corpus_builder.extract.hasher import sha256


def test_known_hash():
    text = "IDENTIFICATION DIVISION."
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert sha256(text) == expected


def test_empty_string():
    expected = hashlib.sha256(b"").hexdigest()
    assert sha256("") == expected


def test_deterministic():
    text = "MOVE A TO B."
    assert sha256(text) == sha256(text)


def test_different_inputs():
    assert sha256("A") != sha256("B")
