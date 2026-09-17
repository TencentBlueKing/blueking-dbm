# 组件目录必须 kebab-case，不要用 PascalCase

- **命中**：本次新建或重命名带 `Index.vue` 的组件目录；或改动的 import 里出现 `/PascalCase/` 目录段。目录段判据：以大写开头、含小写、无连字符（`OperateClusterConfirmDialog`、`RenderSql`）。工具箱提单目录 `{TICKET_TYPE}` 是全大写+下划线，不是本条。也能用：

  ```bash
  find src -type d | python3 -c "
  import sys, re
  pat = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
  all_caps = re.compile(r'^[A-Z][A-Z0-9_]*$')
  for d in sys.stdin:
      d = d.strip()
      for s in d.split('/'):
          if pat.match(s) and not all_caps.match(s):
              print(d)
              break
  "
  ```

  import 路径：`rg -n "from ['\"][^'\"]*/[A-Z][a-z]+[A-Za-z]*/" src`

  `eslint.config.mjs` 的 `no-restricted-imports` 也会在 import 路径含 `/PascalCase/` 目录段时报 error。

- **为什么**：AGENTS.md / create-component 约定组件目录 kebab-case、入口 `Index.vue`。PascalCase 目录和「子组件文件 PascalCase」撞车，import 别名、全局搜索、跨模块复用都会对不上旁边的 `cluster-selector` / `cluster-tag`。

- **改成**：目录改成全小写+连字符，再改引用。已跟踪文件用 `git mv`。模板里的组件名仍用 PascalCase：

  ```
  src/views/db-manage/common/operate-cluster-confirm-dialog/Index.vue
  import Foo from '@views/db-manage/common/operate-cluster-confirm-dialog/Index.vue';
  <OperateClusterConfirmDialog />
  ```

- **不要**：
  - 不要把 `{TICKET_TYPE}` 提单目录（如 `MYSQL_OPEN_AREA`）改成 kebab-case，那是枚举值，见 AGENTS.md
  - 不要把子组件文件 `SubPart.vue` 改成 kebab-case，文件可以 PascalCase
  - 不要只改 import 不改目录，或反过来只改目录

- **存量**：上面两条命令即列表。2026-09-17 改完 `operate-cluster-confirm-dialog` 后，只剩 1 处：
  `src/views/db-manage/sqlserver/SQLSERVER_IMPORT_SQLFILE/components/execute-objects/components/RenderSql`
  （引用在 `src/views/db-manage/sqlserver/SQLSERVER_IMPORT_SQLFILE/components/execute-objects/Index.vue`：
  `import RenderSql from './components/RenderSql/Index.vue'`。find 还会打出它下面的子目录，都挂在这一处下面，不算新实例）

- **核实**：2026-09-17
