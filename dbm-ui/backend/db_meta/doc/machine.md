# 结构
```python
class Machine(models.Model):
    ip = models.GenericIPAddressField(primary_key=True, default='')
    app = models.ForeignKey(
        App,
        to_field='name',
        on_delete=models.PROTECT,
        db_column='app'
    )
    meta_type = models.ForeignKey(
        MetaType,
        to_field='name',
        db_column='meta_type',
        on_delete=models.PROTECT)
```

* 地理信息相关的属性都只是占位, 后续再添加实现
* 当一台机器绑定了特定的 _meta type_, 就代表
  * 绑定了 _meta type_ 对应的 _meta cluster type_
  * 绑定了 _meta type_ 对应的 _meta layer_ 
  
  参考 [MetaType](meta_type.md)

| 属性          | 说明                         |
|-------------|----------------------------|
| _ip_        | _ip_ 地址                    |
| _app_       | 机器所属的业务, 关联到 _app.name_    |
| _meta_type_ | 见 [MetaType](meta_type.md) |

# _api_
_backend/cmdb/api/machine/apis.py_
## _create_
* 添加机器
* 可以批量添加
### 参数
以如下的 _List_ 作为输入
```json
[
  {
    'ip': string,
    'app': string,
    'meta_type': string
  }
]
```

| 属性          | 类型  | 必要  | 说明                  |
|-------------|-----|-----|---------------------|
| _ip_        | 字符串 | 是   | 符合 _ip_ 地址规则的字符串    |
| _app_       | 字符串 | 是   | 业务简称, 必须已存在         |
| _meta_type_ | 字符串 | 是   | 机器类型, 枚举 `MetaType` |

## _query_
查询机器
### 参数
略


## _update_
修改机器信息
机器的大部分信息其实都没啥好改的, 如果未来的机器配置信息需要录入, 而且可以原地升降, 则可以提供接口修改

未实现

## _delete_
未实现