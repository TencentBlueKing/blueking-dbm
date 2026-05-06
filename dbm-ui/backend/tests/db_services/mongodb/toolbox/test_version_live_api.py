# -*- coding: utf-8 -*-
import os

import pytest
import requests
from requests.exceptions import RequestException

BASE_URL = os.getenv("DBM_API_BASE_URL", "http://127.0.0.1:8090").rstrip("/")
BK_BIZ_ID = os.getenv("DBM_TEST_BK_BIZ_ID")
CLUSTER_ID = os.getenv("DBM_TEST_MONGO_CLUSTER_ID")
API_TOKEN = os.getenv("DBM_API_TOKEN", "")
REQUEST_TIMEOUT = int(os.getenv("DBM_API_TIMEOUT", "15"))
RUN_LIVE_API_TEST = os.getenv("RUN_LIVE_API_TEST", "0") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not RUN_LIVE_API_TEST, reason="set RUN_LIVE_API_TEST=1 to enable live API integration tests"),
]


@pytest.fixture(scope="module")
def live_client():
    session = requests.Session()
    if API_TOKEN:
        session.headers.update({"X-API-KEY": API_TOKEN})
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module", autouse=True)
def ensure_live_server(live_client):
    try:
        live_client.get("{}/".format(BASE_URL), timeout=3)
    except RequestException:
        pytest.skip("live server is unavailable: {}".format(BASE_URL))


@pytest.mark.skipif(not BK_BIZ_ID or not CLUSTER_ID, reason="need DBM_TEST_BK_BIZ_ID and DBM_TEST_MONGO_CLUSTER_ID")
def test_list_available_versions_live_api(live_client):
    url = "{}/apis/mongodb/bizs/{}/toolbox/list_available_versions/".format(BASE_URL, BK_BIZ_ID)
    resp = live_client.get(url, params={"cluster_id": CLUSTER_ID}, timeout=REQUEST_TIMEOUT)

    assert resp.status_code == 200
    body = resp.json()
    assert "code" in body
    assert body["code"] == 0
    assert isinstance(body.get("data"), list)
    for row in body["data"]:
        assert isinstance(row, dict)
        assert "major" in row and "full_list" in row
        assert isinstance(row["major"], str)
        assert isinstance(row["full_list"], list)
        assert all(isinstance(v, str) for v in row["full_list"])


def test_list_available_versions_live_api_missing_param(live_client):
    url = "{}/apis/mongodb/bizs/{}/toolbox/list_available_versions/".format(BASE_URL, BK_BIZ_ID or "0")
    resp = live_client.get(url, timeout=REQUEST_TIMEOUT)

    # 参数缺失应由 DRF serializer 拦截；鉴权开启时也允许先返回 401/403
    assert resp.status_code in (400, 401, 403)
