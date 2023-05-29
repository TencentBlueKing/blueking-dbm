![](docs/resource/img/logo_zh.png)
---
[![license](https://img.shields.io/badge/license-MIT-brightgreen.svg)](https://github.com/TencentBlueKing/blueking-dbm/blob/master/LICENSE)
[![Release](https://img.shields.io/badge/release-1.0.0-brightgreen.svg)](https://github.com/TencentBlueKing/blueking-dbm/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/TencentBlueKing/blueking-dbm/pulls)

[English](readme_en.md) | 简体中文

DBM，数据库管理，集成了MySQL、Redis、ES、Kafka、HDFS、InfluxDB、Pulsar等多种数据库组件的全生命周期管理，提供了海量集群的批量管理能力，以及相应DB组件的集群管理工具箱，并配套DB个性化配置、高可用切换、域名管理等DB个性化服务，同时全方位的监控告警可观测能力，让数据库管理员、运维、开发等用户可以轻松完成数据库管理工作，更高效、更安全、更全面的管理数据库。

## Overview
- 设计理念
- 架构设计
- 代码目录

## Features
- 全面的DB组件服务：DBM提供MySQL、Redis、ES、Kafka、HDFS、InfluxDB、Pulsar等多个DB组件管理服务，管理员可按需使用特定DB组件提供全生命周期管理服务。
- 完整的DB工具箱：管理员通过DBM管理每个DB组件，每个DB组件均提供完整的功能服务如集群部署、集群管理、集群扩缩容、集群变更、集群监控等。
- 完善的DB公共管理：DBM提供DB个性化配置管理、高可用切换管理、域名解析管理、DB监控管理等DB公共管理服务，为每个DB组件和用户提供完善的DB基础服务。
- 可交互的执行服务：清晰的任务流程，用户可通过DBM提交所需的DB服务并由管理员审批执行。
- 安全的权限管理：管理员通过DBM可配置每个接入业务的管理员角色，同时提供平台级管理角色配置，权限控制安全可靠。

## Getting started
- [开发环境后台部署](docs/install/dev_deploy.md)

## Version plan
- [版本日志](docs/release.md)


## Support
- [源码](https://github.com/TencentBlueKing/blueking-dbm/tree/master)
- [wiki](https://github.com/TencentBlueKing/blueking-dbm/wiki)
- [蓝鲸论坛](https://bk.tencent.com/s-mart/community)
- [蓝鲸 DevOps 在线视频教程](https://bk.tencent.com/s-mart/video/)
- [蓝鲸社区版交流1群](https://jq.qq.com/?_wv=1027&k=5zk8F7G)

## BlueKing Community
- [BK-CMDB](https://github.com/Tencent/bk-cmdb)：蓝鲸配置平台（蓝鲸 CMDB）是一个面向资产及应用的企业级配置管理平台。
- [BK-CI](https://github.com/Tencent/bk-ci)：蓝鲸持续集成平台是一个开源的持续集成和持续交付系统，可以轻松将你的研发流程呈现到你面前。
- [BK-BCS](https://github.com/Tencent/bk-bcs)：蓝鲸容器管理平台是以容器技术为基础，为微服务业务提供编排管理的基础服务平台。
- [BK-PaaS](https://github.com/Tencent/bk-paas)：蓝鲸 PaaS 平台是一个开放式的开发平台，让开发者可以方便快捷地创建、开发、部署和管理 SaaS 应用。
- [BK-SOPS](https://github.com/Tencent/bk-sops)：标准运维（SOPS）是通过可视化的图形界面进行任务流程编排和执行的系统，是蓝鲸体系中一款轻量级的调度编排类 SaaS 产品。
- [BK-JOB](https://github.com/Tencent/bk-job)：蓝鲸作业平台(Job)是一套运维脚本管理系统，具备海量任务并发处理能力。

## Contributing
如果你有好的意见或建议，欢迎给我们提 Issues 或 Pull Requests，为蓝鲸开源社区贡献力量。关于 蓝鲸数据库管理平台 分支管理、Issue 以及 PR 规范，
请阅读 [Contributing Guide](.github/CONTRIBUTING.md)。

[腾讯开源激励计划](https://opensource.tencent.com/contribution) 鼓励开发者的参与和贡献，期待你的加入。

## License
项目基于 MIT 协议， 详细请参考 [LICENSE](https://github.com/TencentBlueKing/blueking-dbm/blob/master/LICENSE) 。
我们承诺未来不会更改适用于交付给任何人的当前项目版本的开源许可证（MIT 协议）。
