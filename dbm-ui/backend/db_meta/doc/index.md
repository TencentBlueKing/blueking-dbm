# _Meta_
`MetaLayer, MetaClusterType, MetaType, MetaRole` 是 _cmdb_ 的静态元数据, 需要人工录入才能正常工作

1. 表达数据访问层级的 [MetaLayer](meta_layer.md)
2. 表达集群类型的 [MetaClusterType](meta_cluster_type.md)
3. 表达机器类型的 [MetaType](meta_type.md)
4. 表达数据同步关系的 [MetaRole](meta_role.md)

## _apis_
_backend/cmdb/api/meta/apis.py_

只提供了一个 _query_ 接口, 无参数, 返回 _meta_ 数据

## 不可修改和删除
这 _4_ 个元数据为了方便阅读, 都是基于明文和其他表做的外键关联. 被具体的机器和实例引用后就不能随意删除和修改了

# 关于 _api query_ 的说明
* 下面提到的所有模块默认都会提供 _query_ 接口
* 输入参数默认情况都是由模块的各属性构成的 _List_, 每个 _List_ 都是可选项并构成 _or_ 条件的查询
* 返回值默认都是模块对象 _JSON_ 序列化后的 _List_
* 无任何条件的查询返回所有对象
* 如果模块关联到其他模块, 则会做递归序列化返回. 如查询机器信息的返回
  ```json
  [
    {
      "ip": "127.0.0.1",
      "app": {
        "cc_id": 1,
        "fullname": "测试业务1",
        "name": "testapp1"
      },
      "meta_type": {
        "name": "remote",
        "meta_cluster_type": {
          "name": "tendbcluster"
        },
        "meta_layer": {
          "name": "storage"
        }
      }
    }
  ]
  ```
* 输入参数如果是关联到其他模块的属性, 并没有做存在性的校验. 如查询 `Machine` 如果输入了一个不存在的 _app.name_ 并不会抛出 _app not exists_ 的异常, 而是得到一个空结果
* 如有特殊情况会在相应文档中特别说明

# 关于 _api delete_ 的说明
* 并不是所有的模块都会提供 _delete_ 接口
* 某些模块会提供含有 _DELETE_ 语义的接口, 如 `Domain` 的 _unbind_
* 所有 _DELETE_ 语义的接口都只接收具有唯一性的筛选条件, 不提供匹配性的接口. 以 _sql_ 为例子
  ```sql
  -- 这样的筛选是匹配性的, 无法确定会删除哪些对象, 所以是不支持的
  DELETE FROM machine WHERE city = '深圳'
  ```
  ```sql
  -- 这样的筛选是明确的, 因为 ip 是 machine 的唯一表示, 是支持的
  DELETE FROM machine WHERE ip IN ('127.0.0.1', '2.2.2.2')
  ```
# 关于 _api update_ 的说明
_update_ 在输入参数筛选性上的设计和 _delete_ 是一样的

# _App_

描述业务基本信息的 [App](app.md)

# _Machine_
描述机器信息的 [Machine](machine.md)

# _Domain_
描述域名及其 _bind_ 信息的 [Domain](domain.md)

# _StorageInstance_
描述 `存储层` 实例的 [StorageInstance](storageinstance.md)

# _StorageInstanceTuple_
描述 `存储层` 数据同步关系的 [StorageInstanceTuple](storageinstancetuple.md)

# _ProxyInstance_
描述 `接入层` 实例的 [ProxyInstance](proxyinstance.md)

# _Cluster_
描述集群信息的 [Cluster](cluster.md)

# _How To_
## _Meta_ 数据哪里来
* _python manage.py loaddata backend/cmdb/fixtures/init_demo.yaml_ 可以加载一份预定义的数据用于开发测试
* 实际部署需要人工录入
* 这份 _demo_ 数据其实已经能满足一部分生产需求

## 接着要干啥
真实的模拟线上场景, 接着要做的是
1. 新增一个业务
2. 针对想要的 `ClusterType` 添加几台对应 `MetaType` 的机器
3. 添加几个实例
4. 新建一个集群


## 如何知道增加的机器或者实例是什么类型
调用 _meta_ 的 _query_ 接口查询