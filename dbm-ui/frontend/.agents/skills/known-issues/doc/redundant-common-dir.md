# 没有兄弟目录时 common/ 这层不该留

- **命中**：某个 `common/` 是它父目录下唯一的内容——既没有兄弟目录，也没有兄弟文件。**本次改动删掉或搬走了兄弟目录时必须查一遍**，因为这层是那时候变成多余的：

  ```bash
  find src -type d -name common | while read d; do p=$(dirname "$d");
    [ "$(find "$p" -maxdepth 1 -mindepth 1 -type d | wc -l)" -eq 1 ] &&
    [ "$(find "$p" -maxdepth 1 -mindepth 1 -type f | wc -l)" -eq 0 ] && echo "$d"; done
  ```

  父目录下还有别的目录或文件时不算命中——那时 `common/` 确实在区分「共用的」和「某一家专用的」。

- **为什么**：`common/` 的语义是「多个兄弟共用」。没有兄弟可共用时它不区分任何东西，只把 import 路径拉长一级，于是出现 `from '../../../Index.vue'` 这种数不清层数的相对路径，重构挪动文件时极易改错，而且改错了 TS 未必报错（同名 `Index.vue` 在多层目录里都存在）。

- **改成**：`common/` 下内容整体上提一层，删掉 `common/`，然后改三类引用：
  1. 外部对 `<模块>/components/common/X` 的引用去掉 `common/`
  2. 原 `common/` 下文件里指向模块根的 `'../../Index.vue'` 少一级，变 `'../Index.vue'`
  3. 原 `common/<子目录>/` 下的 `'../../../Index.vue'` 同样少一级

  已跟踪的文件用 `git mv` 保留改名历史，未跟踪的用 `mv`。改完 `rg -n "<模块>/components/common"` 应为空，再跑 `yarn type-check` 确认没有新增错误（路径写错会报 TS2307）。

- **不要**：连 `components/` 一起去掉、把子文件平铺到组件根目录。AGENTS.md 要求「仅本组件使用的子文件放同级 `components/`」，`components/` 这层是约定，`common/` 才是多余的那层。

- **存量**：上面的命令即列表。2026-09-15 跑出 1 处：
  `src/views/db-manage/tendb-cluster/common/spider-instance-selector/common`
  （父目录 `spider-instance-selector/` 下只有这一个 `common/`，且它本身已经在一个 `common/` 里面）

- **核实**：2026-09-15

## 补充

本条来自 `src/components/cluster-selector` 的重构：原先 `components/` 下有 `common/` 加 11 个按数据库分的目录（`redis/`、`tendbha/`…），`common/` 名副其实；11 个目录被合并成一个通用 `ClusterTable.vue` 后，`components/` 下只剩 `common/`，这层就没有意义了。合并目录类的重构都该顺手查这一条。
