"""Section 63, Bharatiya Sakshya Adhiniyam 2023 certificate generation.

Per CLAUDE.md section 4.2: "A raw system-generated PDF is not court-admissible.
Under Section 63 of the Bharatiya Sakshya Adhiniyam 2023 (which replaced
Evidence Act s.65B on 1 July 2024) an electronic record needs a signed,
timestamped certificate identifying the device, the production process and
the integrity of the record. Generate that certificate alongside the report.
Claim the record is certifiable, not automatically court-proven."

The "signature" here is an HMAC-SHA256 over the certificate's own fields,
keyed by a server-side secret (LMD_EVIDENCE_SIGNING_KEY). This proves the
certificate was produced by this system and has not been altered since --
it is NOT a PKI digital signature / DSC bound to a legal officer's identity,
and the certificate wording says so explicitly. Overclaiming a real DSC here
would violate CLAUDE.md's honest-claims register.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

_DEV_INSECURE_KEY = b"DEV-INSECURE-KEY-DO-NOT-USE-IN-PRODUCTION"

CERTIFICATE_DISCLAIMER = (
    "This certificate attests that this electronic record was produced by an "
    "automated system, identifies the producing device and process, and has "
    "not been altered since generation (verifiable via the accompanying "
    "SHA-256 hash and HMAC signature). It supports admissibility under "
    "Section 63 of the Bharatiya Sakshya Adhiniyam 2023; it does not itself "
    "constitute a court determination of admissibility or of the underlying "
    "facts, and it is not a Digital Signature Certificate bound to an "
    "individual officer's legal identity."
)

PDF_FOOTER_DISCLAIMER = (
    "This document is system-generated and certified under Section 63, BSA 2023. "
    "Authenticate using the QR code."
)


def _signing_key() -> bytes:
    env_key = os.environ.get("LMD_EVIDENCE_SIGNING_KEY")
    if env_key:
        return env_key.encode("utf-8")
    return _DEV_INSECURE_KEY


def _canonical_payload(
    certificate_id: str,
    device_identification: str,
    production_process_description: str,
    certifying_officer: str,
    generated_at: str,
    record_sha256: str,
) -> str:
    return "|".join(
        [
            certificate_id,
            device_identification,
            production_process_description,
            certifying_officer,
            generated_at,
            record_sha256,
        ]
    )


@dataclass
class Bsa63Certificate:
    certificate_id: str
    device_identification: str
    production_process_description: str
    certifying_officer: str
    generated_at: str
    record_sha256: str
    hmac_signature: str
    disclaimer: str = CERTIFICATE_DISCLAIMER

    def to_dict(self) -> dict:
        return {
            "certificate_id": self.certificate_id,
            "device_identification": self.device_identification,
            "production_process_description": self.production_process_description,
            "certifying_officer": self.certifying_officer,
            "generated_at": self.generated_at,
            "record_sha256": self.record_sha256,
            "hmac_signature": self.hmac_signature,
            "disclaimer": self.disclaimer,
        }


def generate_certificate(
    device_identification: str,
    production_process_description: str,
    record_sha256: str,
    certifying_officer: str = "SYSTEM-GENERATED",
) -> Bsa63Certificate:
    certificate_id = str(uuid.uuid4())
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = _canonical_payload(
        certificate_id,
        device_identification,
        production_process_description,
        certifying_officer,
        generated_at,
        record_sha256,
    )
    signature = hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return Bsa63Certificate(
        certificate_id=certificate_id,
        device_identification=device_identification,
        production_process_description=production_process_description,
        certifying_officer=certifying_officer,
        generated_at=generated_at,
        record_sha256=record_sha256,
        hmac_signature=signature,
    )


def verify_certificate(cert: Bsa63Certificate) -> bool:
    payload = _canonical_payload(
        cert.certificate_id,
        cert.device_identification,
        cert.production_process_description,
        cert.certifying_officer,
        cert.generated_at,
        cert.record_sha256,
    )
    expected = hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, cert.hmac_signature)
