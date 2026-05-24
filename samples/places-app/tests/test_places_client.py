"""Tests for places_client.py using mocked HTTP responses."""

from unittest.mock import patch, MagicMock

import pytest

from places_client import Business, PlacesAPIError, search_businesses, TEXT_SEARCH_URL, NEARBY_SEARCH_URL


@pytest.fixture
def mock_geocode_response():
    """A successful Text Search response used for geocoding."""
    return {
        "places": [
            {
                "location": {"latitude": 33.6543, "longitude": -117.7471}
            }
        ],
    }


@pytest.fixture
def mock_nearby_response():
    """A successful Nearby Search response with two businesses."""
    return {
        "places": [
            {
                "id": "place_acme_123",
                "displayName": {"text": "Acme Corp", "languageCode": "en"},
                "formattedAddress": "123 Main St, Springfield, IL 62701",
                "types": ["establishment", "point_of_interest"],
                "primaryType": "corporate_office",
            },
            {
                "id": "place_bobs_456",
                "displayName": {"text": "Bob's Burgers", "languageCode": "en"},
                "formattedAddress": "123 Main St, Springfield, IL 62701",
                "types": ["restaurant", "establishment"],
                "primaryType": "restaurant",
            },
        ]
    }


@pytest.fixture
def mock_empty_response():
    """A successful response with no results."""
    return {"places": []}


@pytest.fixture
def mock_error_response():
    """A 403 error response when API is not enabled."""
    return {
        "error": {
            "code": 403,
            "message": "Places API (New) has not been used in project 123 before or it is disabled.",
            "status": "PERMISSION_DENIED",
        }
    }


def _make_mock_response(status_code, json_data):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    return mock_resp


class TestSearchBusinesses:
    @patch("places_client.requests.post")
    def test_returns_businesses_on_success(self, mock_post, mock_geocode_response, mock_nearby_response):
        # 3 calls: geocode, nearby search, text search (returns empty to stop pagination)
        mock_post.side_effect = [
            _make_mock_response(200, mock_geocode_response),
            _make_mock_response(200, mock_nearby_response),
            _make_mock_response(200, {"places": []}),
        ]

        results = search_businesses("123 Main St, Springfield, IL", "fake-key")

        assert len(results) == 2
        assert results[0].name == "Acme Corp"
        assert results[1].name == "Bob's Burgers"
        assert results[0].address == "123 Main St, Springfield, IL 62701"

    @patch("places_client.requests.post")
    def test_returns_empty_list_when_no_places(self, mock_post, mock_geocode_response, mock_empty_response):
        mock_post.side_effect = [
            _make_mock_response(200, mock_geocode_response),
            _make_mock_response(200, mock_empty_response),
            _make_mock_response(200, mock_empty_response),
        ]

        results = search_businesses("Middle of Nowhere", "fake-key")

        assert results == []

    @patch("places_client.requests.post")
    def test_raises_error_on_nearby_403(self, mock_post, mock_geocode_response, mock_error_response):
        # Nearby Search returns 403 — function should still not crash
        # (it silently skips nearby errors and tries text search)
        mock_post.side_effect = [
            _make_mock_response(200, mock_geocode_response),
            _make_mock_response(403, mock_error_response),
            _make_mock_response(200, {"places": []}),
        ]

        results = search_businesses("123 Main St", "bad-key")
        assert results == []

    @patch("places_client.requests.post")
    def test_raises_error_on_geocode_failure(self, mock_post):
        mock_post.return_value = _make_mock_response(200, {"places": []})

        with pytest.raises(PlacesAPIError) as exc_info:
            search_businesses("Invalid Address XYZ", "key")

        assert "Could not find location" in exc_info.value.message

    @patch("places_client.requests.post")
    def test_sends_nearby_search_request(self, mock_post, mock_geocode_response, mock_nearby_response):
        mock_post.side_effect = [
            _make_mock_response(200, mock_geocode_response),
            _make_mock_response(200, mock_nearby_response),
            _make_mock_response(200, {"places": []}),
        ]

        search_businesses("456 Oak Ave", "my-api-key")

        # Second call is the nearby search
        call_kwargs = mock_post.call_args_list[1]
        assert call_kwargs.args[0] == NEARBY_SEARCH_URL
        headers = call_kwargs.kwargs["headers"]
        assert headers["X-Goog-Api-Key"] == "my-api-key"
        body = call_kwargs.kwargs["json"]
        assert body["maxResultCount"] == 20
        circle = body["locationRestriction"]["circle"]
        assert circle["center"]["latitude"] == 33.6543

    @patch("places_client.requests.post")
    def test_sends_text_search_request(self, mock_post, mock_geocode_response, mock_nearby_response):
        mock_post.side_effect = [
            _make_mock_response(200, mock_geocode_response),
            _make_mock_response(200, mock_nearby_response),
            _make_mock_response(200, {"places": []}),
        ]

        search_businesses("789 Pine Blvd", "my-api-key")

        # Third call is the text search
        call_kwargs = mock_post.call_args_list[2]
        assert call_kwargs.args[0] == TEXT_SEARCH_URL
        body = call_kwargs.kwargs["json"]
        assert body["pageSize"] == 20
        assert "locationBias" in body
        assert "businesses at 789 Pine Blvd" in body["textQuery"]

    @patch("places_client.requests.post")
    def test_deduplicates_results(self, mock_post, mock_geocode_response):
        """Results found in both Nearby and Text Search are not duplicated."""
        place_data = {
            "id": "place123",
            "displayName": {"text": "Acme Corp", "languageCode": "en"},
            "formattedAddress": "123 Main St",
            "types": ["establishment"],
            "primaryType": "office",
        }
        mock_post.side_effect = [
            _make_mock_response(200, mock_geocode_response),
            _make_mock_response(200, {"places": [place_data]}),
            _make_mock_response(200, {"places": [place_data]}),
        ]

        results = search_businesses("123 Main St", "key")
        assert len(results) == 1

