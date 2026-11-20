# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class JobHostTransData:
    """JobHost 生命周期在 pipeline trans_data 中的上下文。

    实现 set/get，兼容 MongoFastExecScript 等组件对 CommonContext 协议的依赖，
    避免被重置为空的 CommonContext 而丢失 job_host_id / created_this_run。
    """

    job_host_id: Optional[int] = None
    job_host_ip: str = ""
    bk_cloud_id: int = 0
    created_this_run: bool = False
    # 调用方可挂其它字段
    extra: dict = field(default_factory=dict)
    _data: dict = field(default_factory=dict, repr=False)

    def set(self, k, v: Any):
        self._data[k] = v

    def get(self, k):
        return self._data.get(k, None)
