# -*- coding: utf-8 -*-
import hashlib
import logging

from django.conf import settings
from django_redis import get_redis_connection

from backend import env

logger = logging.getLogger("root")

# 前两个集合保存连接和用户的滑动窗口，第三个保存用户并发租约。
# 检查和占用原子执行，避免多进程竞争时超额放行。
ACQUIRE_SCRIPT = """
local now = tonumber(ARGV[7])
local window = tonumber(ARGV[1])
local token = ARGV[5]
for i = 1, 2 do
    redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now - window)
end
redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 1 end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then return 2 end
if redis.call('ZCARD', KEYS[3]) >= tonumber(ARGV[4]) then return 3 end
for i = 1, 2 do
    redis.call('ZADD', KEYS[i], now, token)
    redis.call('PEXPIRE', KEYS[i], window)
end
redis.call('ZADD', KEYS[3], now + tonumber(ARGV[6]), token)
local last = redis.call('ZREVRANGE', KEYS[3], 0, 0, 'WITHSCORES')
redis.call('PEXPIRE', KEYS[3], tonumber(last[2]) - now)
return 0
"""


class CommandLimitExceeded(Exception):
    """达到频率或并发上限，可以稍后重试。"""


class CommandLimitUnavailable(Exception):
    """限流服务异常，禁止绕过限制继续执行。"""


class CommandLimiter:
    """连接额度独立，用户额度跨连接和 WS 进程共享。"""

    def __init__(self, username, connection_id):
        # 隔离应用和租户；同一用户的键使用相同 Redis Cluster 哈希标签。
        identity = f"{env.APP_CODE}:{env.BK_TENANT_ID}:{username}"
        user_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        prefix = f"dbm:ws:webconsole:{{{user_key}}}"
        self.keys = [f"{prefix}:connection:{connection_id}", f"{prefix}:rate", f"{prefix}:active"]
        self.window = int(getattr(settings, "WS_WEBCONSOLE_RATE_WINDOW", 60))
        self.connection_rate = int(getattr(settings, "WS_WEBCONSOLE_CONNECTION_RATE", 10))
        self.user_rate = int(getattr(settings, "WS_WEBCONSOLE_USER_RATE", 30))
        self.user_concurrency = int(getattr(settings, "WS_WEBCONSOLE_USER_CONCURRENCY", 3))
        self.command_timeout = int(getattr(settings, "WS_WEBCONSOLE_COMMAND_TIMEOUT", 21600))
        if min(self.window, self.connection_rate, self.user_rate, self.user_concurrency, self.command_timeout) <= 0:
            raise ValueError("WebConsole 限流和超时配置必须为正整数")

    def acquire(self, token):
        """检查配额并占用并发名额，仅对实际放行的命令计数。"""
        try:
            # 直接访问 Redis，避免 cache 的 IGNORE_EXCEPTIONS 吞掉限流故障。
            redis = get_redis_connection("default")
            # 使用服务端时间；在 Lua 外读取以兼容 Redis 3.0 的写入限制。
            seconds, microseconds = redis.time()
            result = redis.eval(
                ACQUIRE_SCRIPT,
                len(self.keys),
                *self.keys,
                self.window * 1000,
                self.connection_rate,
                self.user_rate,
                self.user_concurrency,
                token,
                # 比执行上限多留一分钟，供连接关闭和异常清理使用。
                (self.command_timeout + 60) * 1000,
                seconds * 1000 + microseconds // 1000,
            )
        except Exception as error:  # pylint: disable=broad-except
            logger.exception("WebConsole 命令限流服务异常")
            raise CommandLimitUnavailable("限流服务暂不可用，请稍后重试") from error
        reasons = {
            1: "当前连接请求过于频繁，请稍后重试",
            2: "当前用户请求过于频繁，请稍后重试",
            3: "当前用户并行命令数已达上限，请稍后重试",
        }
        if result in reasons:
            raise CommandLimitExceeded(reasons[result])
        if result != 0:
            raise CommandLimitUnavailable("限流服务返回异常，请稍后重试")

    def release(self, token):
        """只释放本命令的并发名额，频率记录保留到窗口结束。"""
        try:
            get_redis_connection("default").zrem(self.keys[2], token)
        except Exception:  # pylint: disable=broad-except
            # Redis 故障时由租约回收，释放失败不能触发 SQL 重试。
            logger.exception("WebConsole 并发名额释放失败，将由过期机制回收")
