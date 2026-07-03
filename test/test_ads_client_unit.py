"""Unit tests for ADSClient fixes: set_timeout + err_code handling."""

import pytest
from unittest.mock import MagicMock, patch, call
import pyads

from src.ads_client import ADSClient


@pytest.fixture
def client():
    return ADSClient(
        ams_net_id='192.168.1.1.1.1',
        port=48898,
        timeout=8000,
        route_ip='192.168.1.100',
    )


class TestSetTimeout:
    """Verify set_timeout is called after connection.open() in all paths."""

    @patch('pyads.Connection')
    def test_set_timeout_called_on_normal_connect(self, MockConnection):
        mock_conn = MagicMock()
        MockConnection.return_value = mock_conn

        client = ADSClient(ams_net_id='1.2.3.4.5.6', port=48898, timeout=6000)
        client._open_connection()

        mock_conn.open.assert_called_once()
        mock_conn.set_timeout.assert_called_once_with(6000)
        assert client.connected is True

    @patch('pyads.add_route', side_effect=Exception("already exists"))
    @patch('pyads.Connection')
    def test_set_timeout_called_on_fallback_connect(self, MockConnection, _mock_route):
        mock_conn = MagicMock()
        mock_conn.open.side_effect = [Exception("primary failed"), None]
        MockConnection.return_value = mock_conn

        client = ADSClient(
            ams_net_id='1.2.3.4.5.6', port=48898,
            timeout=10000, route_ip='10.0.0.1',
        )
        client._open_connection()

        assert MockConnection.call_count == 2
        assert mock_conn.open.call_count == 2
        # set_timeout should be called on the successful (fallback) connection
        assert mock_conn.set_timeout.call_count == 1
        mock_conn.set_timeout.assert_called_with(10000)
        assert client.connected is True


class TestHandleAdsError:
    """Verify _handle_ads_error uses err_code and handles error code 1861."""

    def _make_adSError(self, err_code):
        e = pyads.ADSError(err_code=err_code)
        return e

    def test_err_code_1861_timeout(self, client):
        client._connected = True
        e = self._make_adSError(1861)
        client._handle_ads_error(e)
        # 1861 should NOT mark disconnected (it's a transient timeout)
        assert client.connected is True

    def test_err_code_0x07_protocol_timeout(self, client):
        client._connected = True
        e = self._make_adSError(0x07)
        client._handle_ads_error(e)
        assert client.connected is True

    def test_err_code_0x0E_variable_not_found(self, client):
        client._connected = True
        e = self._make_adSError(0x0E)
        client._handle_ads_error(e)
        assert client.connected is True

    def test_err_code_0x01_marks_disconnected(self, client):
        client._connected = True
        e = self._make_adSError(0x01)
        client._handle_ads_error(e)
        assert client.connected is False

    def test_err_code_0x02_marks_disconnected(self, client):
        client._connected = True
        e = self._make_adSError(0x02)
        client._handle_ads_error(e)
        assert client.connected is False

    def test_err_code_0x03_marks_disconnected(self, client):
        client._connected = True
        e = self._make_adSError(0x03)
        client._handle_ads_error(e)
        assert client.connected is False

    def test_unknown_err_code_marks_disconnected(self, client):
        client._connected = True
        e = self._make_adSError(9999)
        client._handle_ads_error(e)
        assert client.connected is False

    def test_old_wrong_attribute_does_not_crash(self):
        """Ensure code no longer uses getattr(e, 'error_code', None)."""
        client = ADSClient(ams_net_id='1.2.3.4.5.6', port=48898)
        e = pyads.ADSError(err_code=1861)
        # The old code did getattr(e, 'error_code', None) which returned None
        # and skipped all branches. Verify err_code is used now.
        assert getattr(e, 'err_code', None) == 1861
        assert getattr(e, 'error_code', None) is None  # old attr doesn't exist


class TestReadByAddress:
    """Verify read calls set_timeout-configured connection and handles errors."""

    @patch('pyads.Connection')
    def test_read_success(self, MockConnection):
        mock_conn = MagicMock()
        mock_conn.read.return_value = True
        MockConnection.return_value = mock_conn

        client = ADSClient(ams_net_id='1.2.3.4.5.6', port=48898, timeout=5000)
        client._open_connection()

        result = client.read_by_address(0x4020, 1, pyads.PLCTYPE_BOOL)
        assert result is True
        mock_conn.read.assert_called_once_with(0x4020, 1, pyads.PLCTYPE_BOOL)

    @patch('pyads.Connection')
    def test_read_timeout_marks_disconnected(self, MockConnection):
        mock_conn = MagicMock()
        mock_conn.open.return_value = None
        mock_conn.set_timeout.return_value = None
        mock_conn.read.side_effect = pyads.ADSError(err_code=1861)
        MockConnection.return_value = mock_conn

        client = ADSClient(ams_net_id='1.2.3.4.5.6', port=48898)
        client._open_connection()

        with pytest.raises(pyads.ADSError):
            client.read_by_address(0x4020, 1, pyads.PLCTYPE_BOOL)

    @patch('pyads.Connection')
    def test_read_connection_error_marks_disconnected(self, MockConnection):
        mock_conn = MagicMock()
        mock_conn.open.return_value = None
        mock_conn.set_timeout.return_value = None
        mock_conn.read.side_effect = pyads.ADSError(err_code=0x01)
        MockConnection.return_value = mock_conn

        client = ADSClient(ams_net_id='1.2.3.4.5.6', port=48898)
        client._open_connection()

        with pytest.raises(pyads.ADSError):
            client.read_by_address(0x4020, 1, pyads.PLCTYPE_BOOL)
        assert client.connected is False
