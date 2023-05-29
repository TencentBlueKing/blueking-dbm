# BKDBM Helm Charts

采用 subchart 模式管理
```
├── Chart.lock
├── Chart.yaml
├── charts
│   ├── dbconfig
│   │   ├── Chart.yaml
│   │   ├── templates
│   │   └── values.yaml
│   ├── dbm
│       ├── Chart.yaml
│       ├── templates
│       └── values.yaml
├── templates
│   ├── NOTES.txt
│   └── _helpers.tpl
└── values.yaml
```

修改后：
1. 执行 `helm dependency update bk-dbm` 更新依赖
2. 执行 `helm template bk-dbm bk-dbm` 渲染 helm template 并校验渲染是否成功
