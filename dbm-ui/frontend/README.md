# 本地开发

## 必要配置

1. 环境变量文件配置
- 需要在 /frontend 目录下面创建 .env.local 文件，推荐配置如下：
```bash
VITE_AJAX_URL_PREFIX='http://bkdbm.paasdb.woa.com'
```
2. 配置host
```bash
127.0.0.1 local.bkdbm.woa.com
```

## 安装依赖

``` bash
yarn
```

## 运行开发环境

``` bash
yarn dev
```

# 生产环境构建

``` bash
yarn build
```
