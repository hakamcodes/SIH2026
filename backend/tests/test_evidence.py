"""SHA-256 hashing/chaining and the Section 63 BSA certificate."""
import hashlib

from lmd.evidence import bsa63, hashing


def test_sha256_bytes_matches_hashlib():
    data = b"hello legal metrology"
    assert hashing.sha256_bytes(data) == hashlib.sha256(data).hexdigest()


def test_sha256_file_matches_bytes(tmp_path):
    p = tmp_path / "evidence.jpg"
    p.write_bytes(b"fake image bytes")
    assert hashing.sha256_file(p) == hashing.sha256_bytes(b"fake image bytes")


def test_chain_next_is_deterministic_and_order_sensitive():
    a = hashing.chain_next(hashing.GENESIS_HASH, "payload-1")
    b = hashing.chain_next(hashing.GENESIS_HASH, "payload-1")
    c = hashing.chain_next(a, "payload-2")
    assert a == b
    assert a != c


def test_verify_chain_detects_tamper():
    h1 = hashing.chain_next(hashing.GENESIS_HASH, "p1")
    h2 = hashing.chain_next(h1, "p2")
    entries = [
        (hashing.GENESIS_HASH, "p1", h1),
        (h1, "p2", h2),
    ]
    assert hashing.verify_chain(entries) is True

    tampered = [
        (hashing.GENESIS_HASH, "p1", h1),
        (h1, "p2-TAMPERED", h2),
    ]
    assert hashing.verify_chain(tampered) is False


def test_certificate_round_trip_verifies():
    cert = bsa63.generate_certificate(
        device_identification="inspector-tablet-IMEI-000000000000000",
        production_process_description="RapidOCR pipeline A + Claude vision pipeline B, reconciled per LM-U02",
        record_sha256=hashing.sha256_bytes(b"the evidence image"),
    )
    assert bsa63.verify_certificate(cert) is True


def test_certificate_tamper_detected():
    cert = bsa63.generate_certificate(
        device_identification="inspector-tablet-1",
        production_process_description="pipeline A + pipeline B",
        record_sha256=hashing.sha256_bytes(b"evidence"),
    )
    cert.production_process_description = "attacker-modified process description"
    assert bsa63.verify_certificate(cert) is False
