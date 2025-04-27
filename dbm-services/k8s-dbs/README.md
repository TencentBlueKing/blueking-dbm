# k8s-dbs

k8s-dbs 是一个基于 Go 客户端和 KubeBlocks API 构建的数据库管控服务，使用 Gin 框架开发。 该服务提供了一系列 RESTful API，允许用户在 Kubernetes 集群中基于 KubeBlocks 组件轻松部署、 管理和操作数据库集群。主要功能包括数据库集群的创建、删除、缩放、启动、停止、重启和升级等。
[说明文档](README.md)

## 快速开始 
### 环境要求
- Go 语言环境（版本 >= 1.18）
- Kubernetes 集群（版本 >= 1.20）
- KubeBlocks 已安装到 Kubernetes 集群——[KubeBlocks安装说明](https://cn.kubeblocks.io/docs/preview/user-docs/installation/install-kubeblocks)