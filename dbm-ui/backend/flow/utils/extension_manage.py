from dataclasses import dataclass
from typing import Optional


@dataclass()
class BigdataManagerKwargs:
    """
    定义大数据Manager活动节点的专属参数
    """

    manager_port: Optional[int] = 0  # manager 端口
    service_type: str = None  # manager 类型
    manager_ip: str = None  # manager ip
    db_type: str = None  # 组件类型
    manager_op_type: str = None  # 操作manager的方式
