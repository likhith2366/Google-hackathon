import asyncio
import httpx
from app.core.config import settings
from app.core.constants import (
    HPD_VIOLATIONS_DATASET,
    DOB_COMPLAINTS_DATASET,
    HPD_LITIGATIONS_DATASET,
    SOCRATA_BASE_URL,
)


async def _fetch_dataset(
    client: httpx.AsyncClient, dataset_id: str, params: dict
) -> tuple[list[dict], bool]:
    """Fetch one Socrata dataset. Returns (data, errored)."""
    url = f"{SOCRATA_BASE_URL}/{dataset_id}.json"
    headers = {"X-App-Token": settings.NYC_OPEN_DATA_TOKEN}
    try:
        response = await client.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json(), False
    except Exception:
        return [], True


async def fetch_all(house_number: str, street_name: str, borough: str) -> dict:
    """
    Fetch HPD violations, DOB complaints, and HPD litigations in parallel.

    Returns:
        {
            "violations": [...],
            "complaints": [...],
            "litigations": [...],
            "data_warning": bool  # True if any dataset fetch errored
        }
    """
    street_upper = street_name.upper()
    hn = house_number

    async with httpx.AsyncClient() as client:
        violations_coro = _fetch_dataset(client, HPD_VIOLATIONS_DATASET, {
            "$where": (
                f"housenumber='{hn}' "
                f"AND streetname LIKE '%{street_upper}%' "
                f"AND violationstatus='Open'"
            ),
            "$limit": 100,
        })
        complaints_coro = _fetch_dataset(client, DOB_COMPLAINTS_DATASET, {
            "$where": (
                f"housenumber='{hn}' "
                f"AND streetname LIKE '%{street_upper}%'"
            ),
            "$limit": 100,
        })
        litigations_coro = _fetch_dataset(client, HPD_LITIGATIONS_DATASET, {
            "$where": (
                f"housenumber='{hn}' "
                f"AND streetname LIKE '%{street_upper}%'"
            ),
            "$limit": 50,
        })

        results = await asyncio.gather(violations_coro, complaints_coro, litigations_coro)

    violations, v_err = results[0]
    complaints, c_err = results[1]
    litigations, l_err = results[2]

    return {
        "violations": violations,
        "complaints": complaints,
        "litigations": litigations,
        "data_warning": any([v_err, c_err, l_err]),
    }
