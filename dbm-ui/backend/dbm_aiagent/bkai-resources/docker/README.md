# DBM AIDEV 初始化镜像

默认基于 `bk-aidev-init:0.1.6`，可通过构建参数 `BKAI_INIT_IMAGE` 覆盖。

Skill Dockerfile 统一写成：

```dockerfile
FROM {{ BKAI_AGENT_IMAGE_REPO }}/bkdbm-aidev-skills-env:0.0.1-alpha.17
```

`BKAI_AGENT_IMAGE_REPO` 是 AIDEV 平台保留变量：bkai-init 打包时保留占位符，由平台在 Skill 上传后渲染为平台镜像仓库地址，入口脚本和部署配置都无需传入。需要 bkai-init 0.1.6 或更新版本。原 `BKAI_SKILL_IMAGE_REPO` / `SKILL_BASE_IMAGE` 环境变量已不再使用。
