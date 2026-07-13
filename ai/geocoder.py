"""
Geocoder — Chuyen doi dia chi thanh toa do (lat/lon).

Su dung Nominatim (OpenStreetMap) — mien phi, khong can API key.
Rate limit: 1 request/giay (tu dong xu ly).

Usage:
    from ai.geocoder import geocode_address

    result = await geocode_address("40 Trung Nu Vuong, Son Tra, Da Nang")
    if result:
        lat, lon, display_name = result
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Rate limiter — Nominatim yeu cau max 1 req/sec
_last_request_time: float = 0.0
_MIN_INTERVAL = 1.1  # seconds

# Nominatim API endpoint
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "SOSFlow-Emergency/1.0 (demo)"


async def geocode_address(
    address: str,
    country_code: str = "vn",
) -> Optional[tuple[float, float, str]]:
    """
    Geocode dia chi thanh toa do.

    Args:
        address: Dia chi can geocode (VD: "40 Trung Nu Vuong, Da Nang")
        country_code: Ma quoc gia (mac dinh: "vn" cho Viet Nam)

    Returns:
        (latitude, longitude, display_name) hoac None neu khong tim thay
    """
    global _last_request_time

    if not address or len(address.strip()) < 3:
        return None

    # Rate limit
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _last_request_time)
    if wait > 0:
        await asyncio.sleep(wait)

    try:
        import httpx

        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": country_code,
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": _USER_AGENT,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            _last_request_time = time.monotonic()
            response = await client.get(
                _NOMINATIM_URL,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            results = response.json()

        if not results:
            logger.debug("Geocode: no results for '%s'", address)
            return None

        best = results[0]
        lat = float(best["lat"])
        lon = float(best["lon"])
        display_name = best.get("display_name", address)

        logger.info(
            "Geocode OK: '%s' -> (%.6f, %.6f) [%s]",
            address, lat, lon, display_name[:60],
        )
        return lat, lon, display_name

    except ImportError:
        logger.warning("httpx not installed, cannot geocode")
        return None
    except Exception as exc:
        logger.warning("Geocode failed for '%s': %s", address, exc)
        return None


async def geocode_location_text(raw_text: str) -> Optional[tuple[float, float, str]]:
    """
    Geocode tu raw_text cua ExtractedLocation.
    Thu nhieu bien the de tang kha nang tim thay.
    """
    if not raw_text:
        return None

    # Thu geocode truc tiep
    result = await geocode_address(raw_text)
    if result:
        return result

    # Them "Da Nang" neu chua co (demo focus vao Da Nang)
    if "da nang" not in raw_text.lower() and "đà nẵng" not in raw_text.lower():
        result = await geocode_address(f"{raw_text}, Da Nang, Viet Nam")
        if result:
            return result

    # Them "Viet Nam" neu chua co
    if "viet nam" not in raw_text.lower() and "việt nam" not in raw_text.lower():
        result = await geocode_address(f"{raw_text}, Viet Nam")
        if result:
            return result

    return None
