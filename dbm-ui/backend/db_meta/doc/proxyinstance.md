# 结构

```python
class ProxyInstance(models.Model):
    port = models.PositiveIntegerField(default=0)
    machine = models.ForeignKey(
        Machine,
        to_field='ip',
        db_column='machine',
        on_delete=models.CASCADE,
    )
    app = models.ForeignKey(
        App,
        to_field='name',
        db_column='app',
        on_delete=models.PROTECT,
    )
    cluster = models.ManyToManyField(Cluster, blank=True)
    storageinstance = models.ManyToManyField(StorageInstance, blank=True)

    class Meta:
        unique_together = ('machine', 'port')
```

* 接入层是没有 `MetaRole` 属性的
* 一个接入层实例可以对应多个存储层实例, 同样的一个存储层实例也可以对应多个接入层

# _api_

_backend/cmdb/api/proxy_instance/apis.py_

## _create_

* 添加实例

### 参数

如下的 _List_ 作为输入

```json
[
  {
    'ip': string,
    'port': int,
    'storage_instances': [
      {
        'ip': string,
        'port': int
      }
    ]
  }
]
```

| 属性                  | 类型   | 必要  | 说明       |
|---------------------|------|-----|----------|
| _ip_                | 字符串  | 是   | 接入层 _ip_ |
| _port_              | 整型   | 是   | 接入层端口    |
| _storage_instances_ | 对象数组 | 否   | 对应的存储层实例 |

_storage_instances_ 结构不专门解释了, 猜也能猜出来了

## _query_
略

## _bind_storage_instance_
添加接入层实例绑定的存储层实例

### 参数

和 _create_ 是一样的

## _unbind_storage_instance_
解绑接入层实例和存储实例

### 参数

和 _create_ 是一样的