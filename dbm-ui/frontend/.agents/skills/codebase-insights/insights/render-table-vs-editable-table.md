# 工具箱编辑表格双轨：render-table 大半已死，editable-table 覆盖不全

状态：已修复（render-table 目录已整体删除，dumper create-rule 迁至 EditableTable，useValidtor 迁入 `src/hooks/`）

## 现象

工具箱提单页的编辑表格存在新旧两套组件：`components/render-table`（旧）与 `components/editable-table`（新）。
`editable-table` 已全局注册（`importComps.ts:69-77`）且是工具箱新代码的唯一选择，但 `render-table` 仍未退场：
名义上 19 处引用里，6 个列组件文件已是死代码或只被死代码引用，活跃使用收缩到 dumper create-rule 一个功能
加 2 处校验 hook。后果：新同事照着 dumper 旧代码会继续引入 render-table；两套校验协议并存
（render-table 是逐单元格 `getValue(): Promise<值>`，editable-table 是 table 级 `validate()` 失败 reject），
与 `validate-failure-contract` 篇目记录的协议混乱互相叠加。

## 证据

### 1. render-table 引用全景（19 处，逐个核实）

活跃（全部集中在两处）：

- 表格壳：`mysql/dumper/components/create-rule/components/receiver-data/Index.vue:186-187`
  import `RenderTable` + `RenderTableHeadColumn`——**全项目唯一的 RenderTable 壳使用点**。
- 单元格控件：dumper create-rule 内 8 个文件（receiver-data 的 6 个 `Render*.vue` 用
  `columns/input`、`columns/select`；subscribe-db-table 的 2 个 TagInput 用 `columns/tag-input`），
  以及 receiver-data `Row.vue:81` 用 `columns/fixed-column`。
- 校验 hook：`mysql/MYSQL_ROLLBACK_CLUSTER/components/backup-mode-column/RecordSelector.vue:148` 与
  `tendb-cluster/TENDBCLUSTER_ROLLBACK_CLUSTER/components/backup-mode-column/RecordSelector.vue:148`
  各 import `hooks/useValidtor`（backup-mode-column 被 6 个回滚页面引用，活跃）。

死代码（自身无人 import，已核实无 `import.meta.glob` 动态引用）：

- `tendb-cluster/common/edit-field/{ClusterName,TableName,DbName}.vue`：全项目 grep `edit-field` 无任何引用；
  它们引用了 `columns/input` 与 `columns/db-table-name`。
- `db-manage/common/sql-execute/common/RenderSql/Index.vue`：无人 import（项目里其他 `RenderSql` 均为各处
  本地同名组件）；它引用了 `columns/text-plain`。
- `db-manage/common/TableSeletorInput.vue`：无人 import；它引用了 `hooks/useValidtor`。

只被死代码引用、随之变孤儿的列组件：`columns/db-table-name`、`columns/text-plain`。
连一条 import 都没有的列组件：`columns/operate-column`、`columns/DateTime`、`columns/element/Index.vue`、
`columns/select-disable`（grep `render-table/columns/(operate-column|DateTime|element|select-disable)` 零匹配；
operate-column 自身还 import 了 fixed-column，但反向无人引用它）。

### 2. 两套协议差异（迁移的真实成本）

- render-table 列控件：`rules` prop + expose `getValue(): Promise<T>`，父组件逐个 ref 收集
  （如 `subscribe-db-table/render-row/DbNameTagInput.vue:63-67`）。校验状态由每个控件自持有。
- editable-table：`model` + `field` 绑定，table 级 `rules`，`validate()` 整表校验、失败 reject
  （`editable-table/Index.vue:255-258`、`Column.vue:553-556`），另支持 `viewError` 后端错误回显、
  rowspan、左右固定列、列宽拖拽、滚动同步。校验协议与 DbForm 对齐。
- render-table 的列控件可脱离表格独立使用（`edit-field/ClusterName.vue:16` 包在普通 div 里）；
  editable-table 的 `edit/*` 组件依赖 `tableInjectKey` / rowContext，必须在 `EditableTable` 内工作，
  不能当独立表单控件。

## 项目里已有的正确做法

`editable-table` 就是正确抽象：全局注册、模型驱动、校验体系完整，工具箱公共列组件
（`views/db-manage/common/toolbox-field/`）与各 DB 的 toolbox-field 全部基于它。它没覆盖到的只有
dumper create-rule 与 2 个 RecordSelector 的 useValidtor 用法。

## 建议方向（未采纳）

1. 先删死代码：edit-field 3 个、sql-execute/common/RenderSql、TableSeletorInput，连带收编
   `columns/{db-table-name,text-plain,operate-column,DateTime,element,select-disable}`。
2. dumper create-rule（receiver-data + subscribe-db-table）迁到 EditableTable：校验从逐个 `getValue()`
   改为 table 级 `validate()`，这是唯一真正的迁移工作。
3. 2 个 RecordSelector 的 `useValidtor` 内联或改写后，删除整个 render-table 目录。
4. 不推荐的做法：把 editable-table 的 `edit/*` 改造成可独立使用来覆盖 render-table 列控件的独立用法——
   独立用法本身全是死代码，没有需要承接的真实场景。

## 待查证

- dumper receiver-data 的批量编辑（BatchEditCommon）与 EditableTable 表头插槽的适配未验证。
- `columns/select-disable`、`columns/element` 等零引用文件是否有历史页面通过字符串模板等非常规方式引用，
  未做运行时验证。
- render-table 的 `HeadColumn.vue` 除 receiver-data 外是否有其他引用，本次只按 `@components/render-table`
  路径扫描，未覆盖所有可能的别名写法。
