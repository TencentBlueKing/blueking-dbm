# DBMeta 代码结构及编写规范

## DBMeta职责
- 维护DB元数据，包括DB集群、实例、机器等数据及关系
- 为 `db_service` 提供部分方法给到前端使用，如集群拓扑关系等
- 为 `flow` 流程提供元数据增删改的方法
- 为 `dbha`、`dbpriv` 等服务提供查询类、操作类接口

## 规定
- 只有 `db_meta.api` 允许对 `Model` 进行写入操作，其他地方不允许进行写入

## 目录结构
backend/db_meta
├── api  // 编写元数据实际操作的方法，包含集群、实例、机器等，主要被`backend.db_service`, `backend.flow`，`backend.db_meta.views`调用
├── doc  // 编写文档
├── enums  // 定义枚举类型
├── flatten  // 通常被`db_meta.api`中的方法引用，用于做关联查询或补充字段
├── models  // 数据模型定义，在`Model`下可编写与此`Model`强相关的 实例方法/类方法
├── request_validator  // 为`backend.db_meta.api`中提供的方法做参数校验
├── validators  // 自定义的校验器
├── views  // 为 `dbha`、`dbpriv` 等服务提供查询类、操作类接口
├── urls.py  // 将`views`中的方法暴露到路由中，需要做服务级别的鉴权（TODO）
└── exceptions.py  // 统一封装DBMeta异常类，抛出异常时使用


## 新增一个集群类型必须实现的代码
- `db_meta.enums.cluster_type`中新增对应的集群类型枚举值
  - 如果该集群类型会引入新的实例角色，则也需在`enums`中添加对应的的枚举值
- 实现集群的 查询类/操作类 的api
  - 在`db_meta.api.cluster`中新建集群类型对应的目录
  - 继承`db_meta.api.cluster.base.hander.ClusterHandler`实现，如`TenDBHAClusterHandler`
  - 「必须」实现的类方法，如`create`, `decommission`, `topo_graph`等方法
  - 「可选」实现集群类型特性的一些方法，如`add_slave`, `delete_slave`
  - 非「必须」的方法，如`list`, `instances`等，视需求实现即可，不必所有集群类型都实现
  - 为避免 `handler` 文件的代码过于臃肿，具体方法的实现可以放在当前定义的集群类型目录下
  - 可复用`db_meta.api`中 对于`StorageInstance`，`ProxyInstance`，`StorageInstanceTuple`，`Machine` 等模型的操作
- 目录结构

backend/db_meta/api/cluster
├── base  // 编写抽象类
│   ├── graph.py
│   └── handler.py  // 集群处理器抽象类
├── tendbha
│   ├── handler.py  // DBHA集群处理器
│   ├── create.py  // 上架集群实现
│   ├── decommission.py  // 下架集群实现
│   └── others.py  // 其它方法
└── tendiscache
│   ├── handler.py  // TendisCache 集群处理器
│   ├── create.py  // 上架集群实现
│   ├── decommission.py  // 下架集群实现
│   └── scale.py  // TendisCache 扩容实现

- ClusterHandler 基类
```python
from abc import ABC
from typing import Optional

from backend.db_meta.models import Cluster


class ClusterHandler(ABC):
    # 「必须」 集群类型
    cluster_type = None

    def __init__(self, bk_biz_id: int, cluster_id: Optional[int] = None):
        self.bk_biz_id = bk_biz_id
        self.cluster_id = cluster_id
        if cluster_id is not None:
            self.cluster: Cluster = Cluster.objects.get(id=cluster_id)

    @classmethod
    def create(cls, *args, **kwargs):
        """「必须」创建集群"""
        raise NotImplementedError

    def decommission(self):
        """「必须」下架集群"""
        raise NotImplementedError

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        raise NotImplementedError
    
    def necessary_method(self):
        """「必须」TODO 待完善"""
        raise NotImplementedError
    
    def optional_method(self):
        """「可选」其他方法，根据集群特性补充"""
        pass

```


## 调用规则/规范
- `backend.db_service`, `backend.flow` 等本 Django 项目内的服务调用
  - `backend.flow`所有操作都按集群维度进行操作，通过 `ClusterHandler` 的方法做函数级调用
  - 具体`StorageInstance`，`ProxyInstance`，`StorageInstanceTuple`，`Machine` 等模型操作的api，仅为`db_meta.api.cluster`和`db_meta.view`（其他独立部署的服务）提供调用服务，不直接被`backend.flow`调用
- 其他独立部署的服务
  - 暴露接口到`urls.py`中，通过 http 请求调用
  - 由于暴露了http接口，可以直接被前端/用户裸调，存在泄漏信息/系统被破坏等安全风险，因此需要做服务间调用鉴权（TODO）
  - 还有一种思路是用同一份代码启动两个工程，其中一个通过ingress暴露接口（前端/用户使用），另一个只暴露service给内部服务（dbha/dbpriv/dbconf等服务）使用，无需做额外鉴权（待确认）