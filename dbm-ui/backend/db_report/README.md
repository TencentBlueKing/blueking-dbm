## 巡检视图

### model 层
1. 报告结果 _model_ 继承 `BaseReportABS`
2. 根据DB路由规则，所有的表会存储在 bk_dbm_report 表中
> 迁移改造：模型层的 `status` 替换成 `state`。


### 视图层
1. 报告结果视图继承 `ReportBaseViewSet`，并且将视图注册 `@register_report(db_type)`
2. 视图开发可以参考 `dbm-ui/backend/db_report/views/mysql/mysqlbackup_check_view.py`，必须定义以下要素：
   - queryset 数据集
   - serializer_class 序列化器
   - report_title 巡检表头
   - report_type 巡检类型

   还有一些可选字段，如过滤排序等，可参考 `ReportBaseViewSet` 的注释说明

> 迁移改造：视图中的 `status` 字段替换成 `state`。并且新增了 `failed_days` 表示失败持续天数。目前先保留 `status` 字段，
> 等各个组件自己改造好后可以把字段换成 `state`。
