# DBM AIDEV 初始化镜像

默认基于 `bk-aidev-init:0.1.4`，可通过构建参数 `BKAI_INIT_IMAGE` 覆盖。

Skill Dockerfile 统一使用 `BKAI_SKILL_IMAGE_REPO` 作为仓库前缀，镜像名和版本保留在 Dockerfile 中。仓库变量必填，值不带末尾 `/`，分隔符在 Dockerfile 中显式定义，例如：

```bash
export BKAI_SKILL_IMAGE_REPO=registry.example.com/team
```

入口脚本通过 `--var BKAI_SKILL_IMAGE_REPO=...` 传给 bkai-init。Dockerfile 使用 `FROM {{ BKAI_SKILL_IMAGE_REPO | required }}/bkdbm-aidev-skills-env:0.0.1-alpha.13`；未配置或为空时校验失败。需要 bkai-init 0.1.4 或更新版本以支持 `required` 过滤器。部署时请将原 `SKILL_BASE_IMAGE` 环境变量改为 `BKAI_SKILL_IMAGE_REPO`。
