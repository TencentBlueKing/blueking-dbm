DBM
===

### 本地开发

- 1. 执行命令（本地启动http服务）

- 需要在 /frontend 目录下面创建 .env.development 文件
```
// 配置 api 域名
VITE_AJAX_URL_PREFIX = "http://api.xxx.com"

``` bash
yarn dev
```

### 生产环境构建

``` bash
yarn build
```
