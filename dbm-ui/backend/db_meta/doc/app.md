# 结构
```python
class App(models.Model):
    fullname = models.CharField(max_length=32, unique=True, default='')
    name = models.CharField(max_length=32, unique=True, default='')
    cc_id = models.BigAutoField(primary_key=True)
```

肯定还缺少属性, 比如负责人. 但不会影响设计所以后续可以添加


| 属性         | 说明                       |
|------------|--------------------------|
| _fullname_ | 业务全称, 只用于展示              |
| _name_     | 业务简称, 代码和 _api_ 全用这个     |
| _cc_id_    | 业务唯一 _id_ , 关联 _cc_ 或没啥用 |

# _api_
_backend/cmdb/api/app/apis.py_
## _create_
新建一个业务
### 参数

| 参数名        | 类型  | 必要  | 说明      |
|------------|-----|-----|---------|
| _fullname_ | 字符串 | 是   | 业务全称    |
| _name_     | 字符串 | 是   | 业务简称    |
| _cc_id_    | 整型  | 否   | 业务 _id_ |

_cc_id_ 设计为可选值是为了做一下兼容
* 对内使用时, 传入明确的值方便和 _cc_ 对接
* 当使用环境没有类似 _cc_ 这样的东西是, 不传入则自动生成没用的唯一 _id_



## _query_
查询业务

### 参数
| 参数名         | 类型    | 必要  | 说明         |
|-------------|-------|-----|------------|
| _fullnames_ | 字符串数组 | 否   | 业务全称列表     |
| _names_     | 字符串数组 | 否   | 业务简称列表     |
| _cc_ids_    | 整型数组  | 否   | 业务 _id_ 列表 |

* _3_ 个输入构成一个 _or_ 查询, 类似 
  ```sql
  SELECT * FROM app WHERE fullname IN [fullnames] or name IN [names] or cc_id IN [cc_ids]
  ```
* 无任何输入的调用返回所有业务
* 大部分时候 _cc_ids_ 这个参数都没啥用

### 返回
```json
[
  {
    'fullname': string,
    'name': string,
    'cc_id': int
  },
  ...
]
```

## _update_
未实现