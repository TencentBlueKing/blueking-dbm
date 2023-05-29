# BK-DataView-Py
BK-Dataview 可提供标准数据源接入, 也是一个标准的grafana frontend程序,  提供grafana代理访问, 完整的权限控制, 动态注入数据源和视图等

## DBM 系统中初始化grafana的步骤
- 向监控获取DBA业务对应的监控数据源token（暂不支持线上获取）
- 打开dbm的grafana代理根路径，且必须带上orgName=dbm参数：/grafana/?orgName=dbm

目前包含 2 个模块
- datasources: 标准数据源接入
- grafana: 代理访问后端grafana服务，可内嵌到其他产品使用，提供完整的权限控制, 动态注入数据源和视图等

## Grafana 特性
- 代理访问
- 自定义用户鉴权&权限控制
- 支持多租户, 无缝对接第三方系统的项目/业务等
- 基于租户的，动态数据源和视图注入
- 内置多种鉴权，注入工具，开箱即用

## 安装依赖
- Python (3.6+)
- django (1.11+)
- requests
- PyYAML

后端依赖Grafana
- 建议版本: Grafana(9.1.x)

## 使用示例

先下载好grafana（测试版本为9.1.8）, 修改配置后，启动服务，grafana 配置参考`bkdbm.ini`
- 解压到安装目录，比如/data
- 拷贝bkdbm.ini到/data/conf目录
- 添加监控数据源插件（可选）
- 启动grafana：./bin/grafana-server -config ./conf/bkdbm.ini

pip install bk-dataview

添加URL配置
```python
# urls.py
from django.conf.urls import include, url

urlpatterns = [
    # grafana访问地址, 需要和grafana前缀保持一致
    url(r"^grafana/", include("bk_dataview.grafana.urls")),
]
```

修改 settings.GRAFANA 配置项
```python
# settings.py
GRAFANA = {
    "HOST": "http://127.0.0.1:3000",
    "PREFIX": "/grafana/",
    "ADMIN": ("admin", "admin"),
    "CODE_INJECTIONS": {
        "<head>": """<head>
<style>
      .sidemenu {
        display: none !important;
      }
      .navbar-page-btn .gicon-dashboard {
        display: none !important;
      }
      .navbar .navbar-buttons--tv {
        display: none !important;
      }
</style>
"""
    }
}
```
配置说明:
- HOST: 访问后端 Grafana 的 IP:Port。
- PREFIX: 访问前缀，需要和Grafana的配置 root_url 保持一致。
- ADMIN： admin账号，默认是("admin", "admin"), 请务必修改 Grafana 配置或者通过 grafana-cli 修改管理员密码。
- CODE_INJECTIONS: 代码注入配置，用于在Grafana的html页面中注入一些代码，实现在不修改Grafana源码的情况下调整Grafana页面。

  默认会注入一段css代码隐藏Grafana的导航栏。

  该配置为字典结构，key和value会作为replace函数的参数。
  ```python
  content = content.replace(key, value)
  ```

访问 Grafana，使用orgName指定访问的业务/项目
```
http://dev.open.examle.com/path/grafana/?orgName=xxx
```

grafana 通过3个步骤控制权限和注入流程
- AUTHENTICATION_CLASSES : 用户认证，验证OK, 在grafana创建用户
- PERMISSION_CLASSES: org_name权限校验, 验证OK，会创建org， 同时把用户加入到当前org
- PROVISIONING_CLASSES: 提供自定义注入dashboard, datasources到当前org


## 自定义用户认证
```python
from bk_dataview.grafana.authentication import BaseAuthentication

class BKAuthentication(BaseAuthentication):
    def authenticate(self, request):
        """
        - return None 用户校验失败
        - return user 对象，用户校验OK
        """
        pass
```

修改配置项目
```python
GRAFANA = {
    "AUTHENTICATION_CLASSES": ["BKAuthentication"],
}
```

已经默认提供的鉴权
- bk_dataview.grafana.authentication.SessionAuthentication
大部分SaaS，在中间件已经做了鉴权，SessionAuthentication只校验是否request.user是否合法

## 自定义权限校验
```python
from bk_dataview.grafana.permissions import BasePermission

class BKPermission(BasePermission):
    def has_permission(self, request, view, org_name: str) -> bool:
        pass
```

修改配置项目
```python
GRAFANA = {
    "PERMISSION_CLASSES": ["BKPermission"],
}
```

已经提供的权限校验
- bk_dataview.grafana.permissions.AllowAny 允许所有
- bk_dataview.grafana.permissions.IsAuthenticated 只校验用户登入态

对线上业务，`请务必实现自己的逻辑`

## 自动注入数据源和Dashboard

### 添加自定义的注入
```python
from bk_dataview.grafana.provisioning import BaseProvisioning, Datasource, Dashboard

class BKProvisioning(BaseProvisioning):
    def datasources(self, request, org_name: str, org_id: int) -> List[Datasource]:
        for x in xxx:
            yield Datasource(**x)

    def dashboards(self, request, org_name: str, org_id: int) -> List[Dashboard]:
        for x in xxx:
            yield Dashboard(**x)
```

Datasource & Dashboard 标准格式
```python
@dataclass
class Datasource:
    """数据源标准格式
    """

    name: str
    type: str
    url: str
    access: str = "direct"
    isDefault: bool = False
    withCredentials: bool = True
    database: Union[None, str] = None
    jsonData: Union[None, Dict] = None
    version: int = 0


@dataclass
class Dashboard:
    """面板标准格式
    """

    title: str
    dashboard: Dict
    folder: str = ""
    folderUid: str = ""
    overwrite: bool = True
```

修改配置项目
```python
GRAFANA = {
    "PROVISIONING_CLASSES": ["BKProvisioning"],
}
```

### SimpleProvisioning
bk_dataview已经默认提供了一个简单的注入，通过配置PROVISIONING_PATH, 系统会自动查找datasource, dashboards配置项

datasources
```yaml
apiVersion: 1
datasources:
  - name: BK-BCS-Prometheus
    type: prometheus
    access: direct
    url: $SETTINGS_DEVOPS_MONITOR_API_URL/api/metric/$ORG_NAME/datasources/data_prometheus/query
    isDefault: true
    withCredentials: true
    jsonData:
      httpMethod: "POST"
```

dashboards
```yaml
apiVersion: 1
providers:
  - name: "default"  # 兼容字段 暂无无实际用处
    folder: ""
    folderUid: ""
    type: file # 兼容字段 暂无无实际用处
    options:
      path: $SETTINGS_BASE_DIR/backend/apps/grafana/dashboards
```

注入可以使用环境变量，语法格式如$ENV_NAME, ${ENV_NAME}, 其他SDK已经添加了系统变量
- ORG_NAME: 组织名，一般是业务id/项目id
- ORG_ID: 组织ID，ORG_NAME对应的id
- SETTINGS_XX: Django的配置项目，只有值是字符串类型是，才能使用

配置具体参考 [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)


## 处理 backend
BACKEND_CLASS: 选择通过API还是DB处理上面的流程，目前支持
- bk_dataview.grafana.backends.api.APIHandler
- bk_dataview.grafana.backends.api.DBHandler

目前差异是 datasources 批量注入, 使用 DBHandler 对大量数据源的注入性能较高

修改配置项目
```python
GRAFANA = {
    "BACKEND_CLASS": "bk_dataview.grafana.backends.api.APIHandler",
}
```

## 本地开发
```bash
# 先fork 到自己的仓库, 再clone到本地

# 本地开发
workon env # 切换到自己的 python环境
python setup.py develop # done, 本地修改后，代码会立即生效

# 欢迎PR
```