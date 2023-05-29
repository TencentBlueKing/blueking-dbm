# 结构
```python
class StorageInstanceTuple(models.Model):
    ejector = models.ForeignKey(
        StorageInstance,
        on_delete=models.CASCADE,
        related_name='ejector',
        db_column='ejector',
    )
    receiver = models.OneToOneField(
        StorageInstance,
        on_delete=models.CASCADE,
        related_name='receiver',
        db_column='receiver',
        unique=True
    )

    class Meta:
        unique_together = ['ejector', 'receiver']
```

* _ejector_ 和 _receiver_ 命名是为了不那么 _mysql_
* _ejector_ 在 _mysql_ 中为 _master_, 发送 _binlog_
* _receiver_ 在 _mysql_ 中为 _slave_, 接受 _binlog_

由于在 `MetaRole` 中提到新增了一个 _repeater_, 所以有如下规则

* _ejector_ 必须是 _master_ 或 _repeater_
* _receiver_ 必须是 _slave_ 或 _repeater_
* _receiver_ 必须是唯一的, 具体到 _db_ 逻辑就是不能多 _master_

# _api_
_backend/cmdb/api/storage_instance_tuple/apis.py_

## _create_
增加同步关系
### 参数
一个如下的 _List_
```json
[
  {
    'ejector_ip': string,
    'ejector_port': int,
    'receiver_ip': string,
    'receiver_port': int,
  }
]
```

属性语义看名字就知道了

## _query_
未实现
传入多个 _ip_ 的时候, 返回值应该是什么样子没想好

## _update_
不应该提供直接的 _update_ 接口

## _delete_
未实现
如何控制删除范围没想好