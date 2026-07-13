"""Deterministic geocoding for the bounded Trà Linh/Đà Nẵng demo scope.

This is deliberately not a production geocoder. It turns a small set of known
demo place names into audited reference coordinates without adding network
latency to emergency intake.
"""

from dataclasses import dataclass
import unicodedata


@dataclass(frozen=True)
class GeocodingSuggestion:
    latitude: float
    longitude: float
    area_code: str
    reference: str
    confidence: float


DEMO_GAZETTEER = {
    "tra linh": GeocodingSuggestion(
        latitude=15.023565,
        longitude=108.041263,
        area_code="TRA_LINH",
        reference="Tâm tham chiếu demo Xã Trà Linh",
        confidence=0.8,
    ),
    "183 phan dang luu": GeocodingSuggestion(
        latitude=16.035971,
        longitude=108.213402,
        area_code="DA_NANG",
        reference="Điểm trực demo PCCC & CNCH Đà Nẵng",
        confidence=0.95,
    ),
    "124 hai phong": GeocodingSuggestion(
        latitude=16.072259,
        longitude=108.216008,
        area_code="DA_NANG",
        reference="Điểm trực demo Bệnh viện Đà Nẵng",
        confidence=0.95,
    ),
}


def _ascii(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def suggest_demo_coordinates(address: str | None) -> GeocodingSuggestion | None:
    if not address:
        return None
    normalized = _ascii(address)
    for phrase, suggestion in DEMO_GAZETTEER.items():
        if phrase in normalized:
            return suggestion
    return None
