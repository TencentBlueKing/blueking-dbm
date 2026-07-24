# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from functools import lru_cache
from typing import Iterable, Sequence

from django_redis import get_redis_connection

# Owner-verified key release: deletes ``KEYS[1]`` only when it still holds
# ``ARGV[1]``. Used by pump / producer pause locks so a stale resume can never
# clobber a lock that was paused again after the original pause was set.
RELEASE_LOCK_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


@lru_cache(maxsize=None)
def compile_script(script: str):
    """Compile a Lua script once (SHA + text).

    The ``default`` Redis connection is used only for encoding the script text
    into the SHA digest and as redis-py's fallback when ``client`` is omitted.
    Always invoke through :func:`eval_script` with an explicit ``client=`` —
    namespace-scoped dispatch keys may live on ``dispatch_N``, not ``default``.
    """
    return get_redis_connection("default").register_script(script)


def eval_script(script_obj, *, client, keys: Sequence = (), args: Iterable = ()):
    """Execute a compiled script on ``client`` (required; never rely on default)."""
    return script_obj(keys=keys, args=args, client=client)
