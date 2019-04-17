"""Segment API tests module."""

import pytest
from splitio.api import segments, client, APIException


class SegmentAPITests(object):
    """Segment API test cases."""

    def test_fetch_segment_changes(self, mocker):
        """Test segment changes fetching API call."""
        httpclient = mocker.Mock(spec=client.HttpClient)
        httpclient.get.return_value = client.HttpResponse(200, '{"prop1": "value1"}')
        segment_api = segments.SegmentsAPI(httpclient, 'some_api_key')
        response = segment_api.fetch_segment('some_segment', 123)

        assert response['prop1'] == 'value1'
        assert httpclient.get.mock_calls == [mocker.call('sdk', '/segmentChanges/some_segment', 'some_api_key', {'since': 123})]

        httpclient.reset_mock()
        def raise_exception(*args, **kwargs):
            raise client.HttpClientException('some_message')
        httpclient.get.side_effect = raise_exception
        with pytest.raises(APIException) as exc_info:
            response = segment_api.fetch_segment('some_segment', 123)
            assert exc_info.type == APIException
            assert exc_info.value.message == 'some_message'
