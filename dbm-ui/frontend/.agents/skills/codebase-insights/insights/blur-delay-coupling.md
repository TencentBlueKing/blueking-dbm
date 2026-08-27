# 标签输入失焦落值：两处硬编码 210ms 耦合 bkui 内部延时

状态：部分处理（自研组件已改为事件驱动，两处 210ms 调用方未改）

## 现象

项目里有两个标签输入组件，业务侧要在「失焦提交残留输入」之后取到最新值：

- bkui 的 `bk-tag-input` 在 blur 后延时 200ms 才把输入框里的残留文字提交成标签（需开 `allowAutoMatch`），再
  `emit('blur')` + `formItem.validate('blur')`；
- 自研的 `DbTagInput` 已改为同步提交，无延时。

`batch-edit-column` 与 `batch-edit-column-new` 两处硬编码 `setTimeout(..., 210)`
排在 bkui 的 200ms 之后，目的就是读到那次提交后的最新值。这个 210ms 既没有常量、也没有类型约束，纯靠注释说明它在等谁：bkui 内部改了延时实现，两处 210ms 不会报错、不会 lint 失败，只会在批量编辑确认时静默拿到旧值。

两处注释的措辞还把矛头指向了自研组件，`batch-edit-column-new/Index.vue:126`
写的是「tag-input 组件内为 200ms 后失焦处理失焦的回调」——没写清是哪个 tag-input，而自研组件现在根本没有延时。

## 证据

| 位置                                                                 | 取值  | 失焦时做什么                                                                                                                          |
| -------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `node_modules/bkui-vue/lib/tag-input/index.js:3860-3885`             | 200ms | 延时后提交残留输入（命中候选则选中，否则 `allowCreate` 时新建），再 `emit('blur', inputValue, tagList)` + `formItem.validate('blur')` |
| `src/components/bkui-vue/tag-input/Index.vue:475-506`                | 无    | 同步提交残留输入，收起标签、关下拉、`emit('blur', residualValue, tagList)` + `formItem.validate('blur')`                              |
| `src/views/db-manage/common/batch-edit-column/Index.vue:198-202`     | 210ms | 等 bkui 提交完再 `handleConfirmChange()`                                                                                              |
| `src/views/db-manage/common/batch-edit-column-new/Index.vue:125-134` | 210ms | 同上                                                                                                                                  |

两处 210ms 的调用方挂的确实是 bkui 组件，且都开了 `allow-auto-match`：

- `batch-edit-column/Index.vue:83-93`：`<BkTagInput ... allow-auto-match allow-create>`
- `batch-edit-column-new/edit/TagInput.vue:2-10`：`<BkTagInput ... allow-auto-match allow-create>`

`BkTagInput` → `DbTagInput` 的替换在本仓库已经发生过：`5bd174001` 把 mysql 与 tendb-cluster 分区管理的 `BkTagInput`
直接换成了 `DbTagInput`。

## 已经收敛掉的一半

自研组件原先在 blur 后也延时 200ms，且延时里做的事与 bkui **语义相反**——丢弃残留文字而不是提交。这个矛盾已消除：

- `handleTriggerMousedown` 对组件内非 input 区域的 mousedown 做 `preventDefault`，焦点不再因点击标签 / `+N`
  / 清空按钮而丢失，blur 只在焦点真正离开组件时触发，兜底延时随之删除；
- `commitResidualInput` 在 blur 时提交残留输入，命中候选的段归一化为候选值，与 bkui 的 `allowAutoMatch` 对齐；
- 对外 `emit('blur', residualValue, tagList)`，残留输入与提交后的标签列表一并给出。

所以现在把两处调用方换成 `DbTagInput` 不再有「残留输入被丢掉」的风险，210ms 只会退化成纯多余的等待。

## 建议方向（未采纳）

让调用方订阅 `@blur` 后再取值，删掉 210ms。不推荐把 200 提成共享常量再让业务方
`+10`：常量化只是让魔法数字有了名字，时序耦合还在。

项目里已有的正确做法：`src/components/editable-table/edit/` 下的 `Input.vue:86-90`、`Select.vue:110-114`、
`TagInput.vue:62-66`、`DatePicker.vue:64-68`、`Textarea.vue:78-82` 是同一套写法——失焦时调用 `columnContext.blur()` +
`columnContext.validate('blur')` 再 `emits('blur')`，父级订阅事件而不是猜时间。这套契约没有覆盖到 `batch-edit-column`
系列，它们不在 EditableTable 体系内。

## 待查证

- 只覆盖了读进上下文的文件：`bkui-vue/tag-input`、`batch-edit-column`、`batch-edit-column-new`、
  `editable-table/edit/*`、mysql 与 tendb-cluster 的
  `partition-manage/components/Operation.vue`。没有全库扫描其它「等失焦落值」的写法。
- `src/components/create-validate-select/Index.vue:189-191` 的 `setTimeout(handleBlurInput, 500)`
  是选项异步到达后补触发失焦，和上面两处的语义不完全相同，是否属于同一类漂移未确认。
- 两处 210ms 的调用方改成订阅 `@blur` 后，`props.validator()` 与 `confirmHandler()` 的执行顺序是否仍然正确，未验证。
