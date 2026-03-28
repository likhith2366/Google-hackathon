from unittest.mock import AsyncMock, patch, MagicMock
from app.services.nyc_service import fetch_all, _fetch_dataset


async def test_fetch_dataset_returns_json_on_success():
    mock_response = MagicMock()
    mock_response.json.return_value = [{"class": "C"}]
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    data, errored = await _fetch_dataset(mock_client, "wv7w-wfz2", {"$limit": 10})

    assert data == [{"class": "C"}]
    assert errored is False


async def test_fetch_dataset_returns_empty_and_true_on_error():
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Network error")

    data, errored = await _fetch_dataset(mock_client, "wv7w-wfz2", {})

    assert data == []
    assert errored is True


async def test_fetch_all_returns_all_three_datasets():
    violations = [{"class": "C"}]
    complaints = [{"complaintcategory": "ELEVATOR"}]
    litigations = [{"casetype": "HP PROCEEDING"}]

    async def fake_fetch(client, dataset_id, params):
        if dataset_id == "wv7w-wfz2":
            return violations, False
        if dataset_id == "8792-6kh6":
            return complaints, False
        if dataset_id == "63ge-vje6":
            return litigations, False

    with patch("app.services.nyc_service._fetch_dataset", side_effect=fake_fetch):
        result = await fetch_all("123", "MAIN ST", "Brooklyn")

    assert result["violations"] == violations
    assert result["complaints"] == complaints
    assert result["litigations"] == litigations
    assert result["data_warning"] is False


async def test_fetch_all_sets_data_warning_when_any_dataset_errors():
    async def fake_fetch(client, dataset_id, params):
        if dataset_id == "wv7w-wfz2":
            return [], True   # error on violations
        return [], False

    with patch("app.services.nyc_service._fetch_dataset", side_effect=fake_fetch):
        result = await fetch_all("123", "MAIN ST", "Brooklyn")

    assert result["data_warning"] is True
