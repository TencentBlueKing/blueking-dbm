# 语言包值里的字面花括号必须转义，不能直接写 {中文} 或 {带空格}

- **命中**：往 `src/locales/*.json` 的值里写 `{` `}` 字面量时；或页面报 `Message compilation error: Invalid token in placeholder: 'xxx'`
- **为什么**：vue-i18n 把值里的 `{xxx}` 当具名插值占位符编译，占位符名只允许标识符字符（字母/数字/下划线），中文或空格直接抛 SyntaxError，整页渲染中断
- **改成**：显示字面花括号用字面量插值转义 `{'{'}集群名{'}'}`（渲染结果 `{集群名}`）。仓库已有 `{'@'}` 同款惯例（zh-cn.json / en.json 各 3 处），vue-i18n 11.4.10 支持
- **不要**：不要把 key 里的花括号去掉再在模板里拼花括号——key 只是查找字符串不会被编译，带花括号的 key 无需改动，多改组件文件是扩大范围
- **存量**：两条命令输出为空即干净（合法的 `{'@'}` 转义不会命中）：
  - `rg -n '": [^"]*\{[^"{}]*[一-鿿]' src/locales`（值的花括号内含中文）
  - `rg -n '": [^"]*\{[A-Za-z0-9_]+ [A-Za-z0-9_ ]+\}' src/locales`（值的花括号内含空格）
- **核实**：2026-09-11

## 补充

实例：`DomainPreview.vue` 的 `t('{集群名}')`，zh-cn 值 `"{集群名}"` 在 TENDBHA 创建模块页（MySql 工厂组件挂载 DomainPreview）抛 `Invalid token in placeholder: '集群名'`；en 值 `{Cluster Name}` 因空格同样非法。数字占位符 `{0}`、标识符占位符 `{n}` / `{max}` 均合法，不在本条范围。
