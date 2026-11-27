# -*- coding: utf-8 -*-
from dataclasses import dataclass, field, fields
from typing import Any, Optional

# bamboo RewritableNode 未解析 / 空初始值常见形态
_EMPTY_TRANS_DATA = (None, "", "${trans_data}")


@dataclass
class ExecHostTransData:
    """ExecHost 生命周期在 pipeline trans_data 中的上下文。

    实现 set/get，兼容 MongoFastExecScript 等组件对 CommonContext 协议的依赖，
    避免被重置为空的 CommonContext 而丢失 exec_host_id / created_this_run。
    """

    exec_host_id: Optional[int] = None
    exec_host_ip: str = ""
    bk_cloud_id: int = 0
    created_this_run: bool = False
    # 调用方可挂其它字段
    extra: dict = field(default_factory=dict)
    _data: dict = field(default_factory=dict, repr=False)

    def set(self, k, v: Any):
        self._data[k] = v

    def get(self, k):
        return self._data.get(k, None)


def coerce_exec_host_trans_data(trans_data: Any) -> ExecHostTransData:
    """Ensure ExecHostTransData: pipeline may pass str/dict/None instead of the dataclass."""
    if isinstance(trans_data, ExecHostTransData):
        return trans_data
    if isinstance(trans_data, dict):
        allowed = {f.name for f in fields(ExecHostTransData) if f.name != "_data"}
        kwargs = {k: v for k, v in trans_data.items() if k in allowed}
        if "extra" in kwargs and not isinstance(kwargs["extra"], dict):
            kwargs["extra"] = {}
        ctx = ExecHostTransData(**kwargs)
        raw = trans_data.get("_data")
        if isinstance(raw, dict):
            ctx._data = raw
        return ctx
    if trans_data in _EMPTY_TRANS_DATA or isinstance(trans_data, str):
        return ExecHostTransData()
    # Unknown object: best-effort wrap empty rather than AttributeError on setattr
    return ExecHostTransData()
