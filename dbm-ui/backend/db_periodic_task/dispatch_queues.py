# -*- coding: utf-8 -*-
"""DispatchQueue implementations owned by the db_periodic_task app."""

from backend.db_periodic_task.dispatch.dummy import DummyTaskQueue
from backend.db_periodic_task.dispatch.portrait_queue import PortraitQueue

__all__ = ["DummyTaskQueue", "PortraitQueue"]
