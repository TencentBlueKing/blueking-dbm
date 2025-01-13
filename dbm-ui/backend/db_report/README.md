1. 报告结果 _model_ 继承 `BaseReportABS`
2. 报告结果视图继承 `ReportBaseViewSet`，并且将视图注册 `@register_report(db_type)`
3. 视图示例可以参考 `dbm-ui/backend/db_report/views/mysql/mysqlbackup_check_view.py`
