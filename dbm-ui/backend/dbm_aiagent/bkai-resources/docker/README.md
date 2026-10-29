# DBM AIDEV 初始化镜像

默认基于 `bk-aidev-init:0.1.5`，可通过构建参数 `BKAI_INIT_IMAGE` 覆盖。

Skill Dockerfile 统一使用：

```dockerfile
FROM {{ BKAI_SKILL_IMAGE_REPO }}/bkdbm-aidev-skills-env:0.0.1-alpha.17
```

`BKAI_SKILL_IMAGE_REPO` 是 AIDEV 平台保留变量，bkai-init（0.1.5 起）打包时原样保留、由平台构建时替换，Job 无需注入，传 `--var` 也会被忽略。

升级 skill 基础镜像时，需要同时修改各 Skill Dockerfile 中的 tag 和 Helm `dbm.bkai.skillsEnvImage.tag`（后者仅用于让流水线同步镜像）。
