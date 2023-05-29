import logging
from typing import Callable, List, Tuple, Union  # noqa. flake8 #118

from django.apps.config import AppConfig
from django.conf import settings
from django.db import utils as django_db_utils
from django.db.backends.base import base as django_db_base
from django.dispatch import Signal

_log = logging.getLogger(__name__)


pre_reconnect = Signal()
post_reconnect = Signal()

_operror_types = ()  # type: Union[Tuple[type], Tuple]
_operror_types += (django_db_utils.OperationalError,)

try:
    import MySQLdb
except ImportError:
    pass
else:
    _operror_types += (MySQLdb.OperationalError,)


def monkeypatch_django() -> None:
    def ensure_connection_with_retries(self: django_db_base.BaseDatabaseWrapper) -> None:
        self._max_dbconn_retry_times = getattr(settings, "MAX_DBCONN_RETRY_TIMES", 1)
        if self.connection is not None and hasattr(self.connection, "closed") and self.connection.closed:
            _log.debug("failed connection detected")
            self.connection = None

        if self.connection is None and not hasattr(self, "_in_connecting"):
            with self.wrap_database_errors:
                try:
                    self._in_connecting = True
                    self.connect()
                except Exception as e:
                    if isinstance(e, _operror_types):
                        if (
                            hasattr(self, "_connection_retries")
                            and self._connection_retries >= self._max_dbconn_retry_times
                        ):
                            _log.error("Reconnecting to the database didn't help %s", str(e))
                            del self._in_connecting
                            post_reconnect.send(self.__class__, dbwrapper=self)
                            raise
                        else:
                            _log.info("Database connection failed. Refreshing...")
                            # mark the retry
                            try:
                                self._connection_retries += 1
                            except AttributeError:
                                self._connection_retries = 1
                            # ensure that we retry the connection. Sometimes .closed isn't set correctly.
                            self.connection = None
                            del self._in_connecting

                            # give libraries like 12factor-vault the chance to update the credentials
                            pre_reconnect.send(self.__class__, dbwrapper=self)
                            self.ensure_connection()
                            post_reconnect.send(self.__class__, dbwrapper=self)
                    else:
                        _log.debug(
                            "Database connection failed, but not due to a known error for dbconn_retry %s", str(e)
                        )
                        del self._in_connecting
                        raise
                else:
                    # connection successful, reset the flag
                    self._connection_retries = 0
                    del self._in_connecting

    _log.debug("django_dbconn_retry: monkeypatching BaseDatabaseWrapper")
    django_db_base.BaseDatabaseWrapper.ensure_connection = ensure_connection_with_retries


class DjangoIntegration(AppConfig):
    name = "backend.django_dbconn_retry"

    def ready(self) -> None:
        monkeypatch_django()
