# bk-dns-api

## 概述
该服务用于提供dbm项目中的dns接口调用
包含以下：
- 域名的增删改查
- dns server的查询


## 常用命令
以下命令需要处于项目根目录下执行
- `go mod download`: 恢复项目依赖，如果已经迁入到 `vendor` 则不需要
- `make init`: 用于初始化一个项目
- `make hook`: 安装预置的git钩子，在`commit`时自动`gofmt`代码
- `make build`: 编译二进制文件
- `make publish [VER=v0.0.1]`: 编译镜像并发布到镜像仓库, *VER* 如果不指定会使用 *v0.0.1*
- `go get somerepo[@version]`: 为你的服务添加或者更新某个依赖
- `go mod -replace=somerepo[@ver]=anotherrepo[@ver] `: 在不修改原依赖的情况替换掉原依赖
- `go mod tidy`: 清理依赖
