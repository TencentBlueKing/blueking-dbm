## 开发测试

#### 单元测试
- 优先以 `ComponentTestMixin` 的形式进行单元测试，参考 `backend/tests/flow/components/mysql`

#### 本地测试
- 通过 `backend/flow/views`, `backend/flow/urls.py` 添加路由的方式进行本地测试
- `ViewSet` 继承 `FlowTestView` (`from backend.flow.views.base import FlowTestView`)
- 仅允许在本地模式中开启 DEBUG 模式 `DEBUG=True`

#### 单据调用
- 单据不会直接调用 `flow.views`
- 通过定义`Builder`和`controller` 与 `flow` 的 `scene` 进行关联，见 `backend/ticket/builders/`