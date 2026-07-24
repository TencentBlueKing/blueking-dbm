from dataclasses import dataclass
from typing import ClassVar
from unittest.mock import patch

import pytest

from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.queue import DEFAULT_NAMESPACE, DispatchQueue


@dataclass
class DefaultNamespaceQueueConfig(DispatchQueueConfig):
    """Give the abstract base queue a real namespace for the duration of a test.

    ``DispatchQueue`` itself declares no namespace, so its keys and Redis
    routing are undefined. Tests drive the base class directly, so bind it to
    ``default`` instead of expecting the framework to guess.
    """

    namespace: ClassVar[str] = DEFAULT_NAMESPACE


@pytest.fixture(autouse=True)
def bind_base_queue_namespace():
    with patch.object(DispatchQueue, "config_cls", DefaultNamespaceQueueConfig):
        yield


@pytest.fixture(autouse=True)
def clear_dispatch_route_cache():
    """Keep the routing memo/cache from leaking across tests.

    With 50+ patch targets repointed at ``routing.conn_for_namespace``, a stale
    memo entry would silently cross-wire namespaces between tests.
    """
    from backend.db_periodic_task.dispatch import routing

    routing.reset_route_cache()
    yield
    routing.reset_route_cache()
