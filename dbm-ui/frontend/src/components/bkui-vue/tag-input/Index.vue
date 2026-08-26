<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="triggerRef"
    class="db-tag-input"
    :class="{
      'is-focus': isFocus,
      'is-disabled': disabled,
    }"
    @click="handleTriggerClick">
    <div
      ref="panelRef"
      class="db-tag-input-panel">
      <div class="db-tag-input-tag-list">
        <BkTag
          v-for="value in visibleTagValues"
          :key="value"
          class="db-tag-input-tag"
          :closable="!disabled"
          @close="handleRemoveTag(value)">
          {{ getValueLabel(value) }}
        </BkTag>
        <BkTag
          v-if="collapsedTagCount > 0"
          class="db-tag-input-tag db-tag-input-overflow-tag"
          @click.stop="handleExpandTags">
          +{{ collapsedTagCount }}
        </BkTag>
        <input
          ref="inputRef"
          v-model="inputValue"
          class="db-tag-input-input"
          :disabled="disabled"
          :placeholder="modelValue.length ? '' : placeholder"
          spellcheck="false"
          @blur="handleInputBlur"
          @focus="handleInputFocus"
          @input="handleInput"
          @keydown="handleKeydown"
          @paste="handlePaste" />
      </div>
      <DbIcon
        v-if="clearable && modelValue.length && !disabled"
        class="db-tag-input-clear"
        type="close-circle-shape"
        @click.stop="handleClear" />
    </div>
    <!-- 隐藏测量区：用于计算 32px 高度内可容纳的最大标签数量 -->
    <div
      ref="measureRef"
      class="db-tag-input-measure"
      :style="{ width: `${triggerWidth}px` }">
      <BkTag
        v-for="value in modelValue"
        :key="value"
        class="db-tag-input-tag db-tag-input-measure-tag"
        :closable="!disabled">
        {{ getValueLabel(value) }}
      </BkTag>
    </div>
    <!-- 下拉内容：作为 tippy.js 挂载源，展示时被移动到 body -->
    <div style="display: none">
      <div
        ref="dropdownRef"
        class="db-tag-input-dropdown-content"
        :style="{ width: dropdownWidth }"
        @mousedown.prevent>
        <div
          v-if="createValue"
          class="db-tag-input-option db-tag-input-create"
          @click="handleCreate">
          <DbIcon type="plus-circle" />
          <span class="db-tag-input-option-label">{{ t('新建') }}「{{ createValue }}」</span>
        </div>
        <template v-if="filteredList.length">
          <div
            v-if="multiple"
            class="db-tag-input-option db-tag-input-select-all"
            @click="handleSelectAll">
            <BkCheckbox
              :indeterminate="selectAllStatus.indeterminate"
              :model-value="selectAllStatus.checked"
              style="pointer-events: none" />
            <span class="db-tag-input-option-label">{{ t('全选（n）', { n: filteredList.length }) }}</span>
          </div>
          <div class="db-tag-input-option-list">
            <div
              v-for="(item, index) in filteredList"
              :key="item.id"
              class="db-tag-input-option"
              :class="{
                'is-highlight': index === highlightIndex,
                'is-selected': !multiple && selectedValueMap[item.id],
              }"
              @click="handleOptionClick(item)"
              @mouseenter="highlightIndex = index">
              <BkCheckbox
                v-if="multiple"
                :model-value="selectedValueMap[item.id]"
                style="pointer-events: none" />
              <span
                v-overflow-tips
                class="db-tag-input-option-label">
                {{ item.name }}
              </span>
              <DbIcon
                v-if="!multiple && selectedValueMap[item.id]"
                class="db-tag-input-option-check"
                type="check-line" />
            </div>
          </div>
        </template>
        <div
          v-else-if="!createValue"
          class="db-tag-input-empty">
          {{ t('无匹配数据') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  interface ListItem {
    id: string;
    name?: string;
  }

  interface Props {
    /** 是否允许输入新建候选外的标签。开启后「仅候选」模式亦可创建新值（回车 / 粘贴不再过滤非法值） */
    allowCreate?: boolean;
    clearable?: boolean;
    /** 候选下拉宽度，不传则跟随触发器宽度 */
    contentWidth?: number;
    disabled?: boolean;
    /** 候选源。提供时默认进入「仅候选」模式 */
    list?: ListItem[];
    /** 组件模式；不传时根据是否提供 list 自动推断。模式按接入场景固定 */
    mode?: 'only-candidate' | 'free-input';
    /** 是否多选。开启时候选项展示为 checkbox 并支持全选；关闭时为单选 */
    multiple?: boolean;
    placeholder?: string;
  }

  type Emits = (e: 'change', value: string[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowCreate: false,
    clearable: true,
    contentWidth: undefined,
    disabled: false,
    list: undefined,
    mode: undefined,
    multiple: false,
    placeholder: '',
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  // 批量粘贴分隔符：逗号、分号、竖线、换行、制表符、空格（含中文全角），连续分隔符产生空段后统一丢弃
  const SEPARATOR_REGEX = /[,，;；、｜|\t\r\n ]/;

  const triggerRef = useTemplateRef('triggerRef');
  const panelRef = useTemplateRef('panelRef');
  const inputRef = useTemplateRef('inputRef');
  const dropdownRef = useTemplateRef('dropdownRef');
  const measureRef = useTemplateRef('measureRef');

  const inputValue = ref('');
  const isFocus = ref(false);
  const highlightIndex = ref(-1);
  const triggerWidth = ref(0);
  const visibleTagCount = ref(0);

  // tippy 下拉实例
  let tippyInstance: Instance | undefined;
  let resizeObserver: ResizeObserver | undefined;

  // 「仅候选」模式：显式指定优先，否则依据是否提供 list 推断
  const isCandidateMode = computed(() => (props.mode ? props.mode === 'only-candidate' : Array.isArray(props.list)));

  const candidateList = computed(() =>
    (props.list ?? []).map((item) => ({
      id: item.id,
      name: item.name ?? item.id,
    })),
  );

  const dropdownWidth = computed(() => `${props.contentWidth ?? triggerWidth.value}px`);

  const visibleTagValues = computed(() =>
    isFocus.value ? modelValue.value : modelValue.value.slice(0, visibleTagCount.value),
  );

  const collapsedTagCount = computed(() =>
    isFocus.value ? 0 : Math.max(0, modelValue.value.length - visibleTagCount.value),
  );

  // 已选值集合，用于去重与选中态判断
  const selectedValueMap = computed(() => Object.fromEntries(modelValue.value.map((value) => [value, true])));

  // 候选值展示名映射
  const candidateNameMap = computed(() => Object.fromEntries(candidateList.value.map((item) => [item.id, item.name])));

  // 关键词包含匹配（不区分大小写）；多个分隔词按 OR 匹配，无关键词展示全部候选
  const filteredList = computed(() => {
    const keywords = inputValue.value
      .split(SEPARATOR_REGEX)
      .map((item) => item.trim().toLowerCase())
      .filter((item) => item.length > 0);
    if (!keywords.length) {
      return candidateList.value;
    }
    return candidateList.value.filter((item) => {
      const name = item.name.toLowerCase();
      return keywords.some((keyword) => name.includes(keyword));
    });
  });

  // 允许新建时，输入词非候选且未选中，则展示「新建」入口
  const createValue = computed(() => {
    if (!props.allowCreate || !isCandidateMode.value) {
      return '';
    }
    const value = inputValue.value.trim();
    if (!value || selectedValueMap.value[value]) {
      return '';
    }
    const isCandidate = candidateList.value.some((item) => item.id === value || item.name === value);
    return isCandidate ? '' : value;
  });

  // 全选三态（相对当前过滤结果）
  const selectAllStatus = computed(() => {
    const list = filteredList.value;
    if (!list.length) {
      return {
        checked: false,
        indeterminate: false,
      };
    }
    const selectedCount = list.filter((item) => selectedValueMap.value[item.id]).length;
    return {
      checked: selectedCount === list.length,
      indeterminate: selectedCount > 0 && selectedCount < list.length,
    };
  });

  /**
   * 计算失焦时单行内可展示的最大标签数量。
   * 预留输入区和清空按钮空间，溢出的标签由 +N 占位。
   */
  const updateVisibleTagCount = () => {
    if (isFocus.value) {
      visibleTagCount.value = modelValue.value.length;
      return;
    }
    nextTick(() => {
      const tagElements = measureRef.value?.querySelectorAll<HTMLElement>('.db-tag-input-measure-tag');
      if (!tagElements?.length || !triggerRef.value) {
        visibleTagCount.value = 0;
        return;
      }

      const GAP_WIDTH = 4;
      const INPUT_RESERVED_WIDTH = 40;
      const PANEL_HORIZONTAL_SPACE = 30;
      const availableWidth = Math.max(0, triggerRef.value.clientWidth - INPUT_RESERVED_WIDTH - PANEL_HORIZONTAL_SPACE);
      let usedWidth = 0;
      let count = 0;

      for (let index = 0; index < tagElements.length; index += 1) {
        const tagWidth = tagElements[index].offsetWidth;
        const remainingCount = tagElements.length - index - 1;
        const overflowWidth = remainingCount > 0 ? 18 + String(remainingCount).length * 7 : 0;
        const tagGap = count > 0 ? GAP_WIDTH : 0;
        const overflowSpace = remainingCount > 0 ? GAP_WIDTH + overflowWidth : 0;
        if (usedWidth + tagGap + tagWidth + overflowSpace > availableWidth) {
          break;
        }
        usedWidth += tagGap + tagWidth;
        count += 1;
      }

      visibleTagCount.value = count;
    });
  };

  // 内容变化后重新计算下拉位置
  const updateDropdownPosition = () => {
    if (tippyInstance?.state.isShown) {
      nextTick(() => {
        tippyInstance?.popperInstance?.update();
      });
    }
  };

  // 过滤结果变化后重置浏览高亮：恰好 1 条自动高亮，其余默认无高亮
  watch(filteredList, (list) => {
    highlightIndex.value = isCandidateMode.value && list.length === 1 ? 0 : -1;
    updateDropdownPosition();
  });

  watch(createValue, () => {
    updateDropdownPosition();
  });

  watch(
    modelValue,
    () => {
      updateVisibleTagCount();
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(highlightIndex, (index) => {
    if (index < 0) {
      return;
    }
    nextTick(() => {
      const optionEls = dropdownRef.value?.querySelectorAll('.db-tag-input-option-list .db-tag-input-option');
      const targetEl = optionEls?.[index] as HTMLElement | undefined;
      targetEl?.scrollIntoView({ block: 'nearest' });
    });
  });

  const getValueLabel = (value: string) => candidateNameMap.value[value] ?? value;

  const emitChange = (value: string[]) => {
    modelValue.value = value;
    emits('change', value);
  };

  // 追加值：批内 + 已选去重
  const appendValues = (values: string[]) => {
    if (!values.length) {
      return;
    }
    // 单选：仅取第一个并替换现有值
    if (!props.multiple) {
      const [first] = values;
      if (modelValue.value[0] !== first) {
        emitChange([first]);
      }
      return;
    }
    const nextValueList = [...modelValue.value];
    const existSet = new Set(nextValueList);
    values.forEach((value) => {
      if (!existSet.has(value)) {
        nextValueList.push(value);
        existSet.add(value);
      }
    });
    if (nextValueList.length !== modelValue.value.length) {
      emitChange(nextValueList);
    }
  };

  const removeValue = (value: string) => {
    emitChange(modelValue.value.filter((item) => item !== value));
  };

  // 校验合法值：去空格后与某一候选项完全一致（匹配 id 或展示名），返回候选值 id
  const resolveCandidateValue = (segment: string) => {
    const value = segment.trim();
    if (!value) {
      return null;
    }
    const matched = candidateList.value.find((item) => item.id === value || item.name === value);
    return matched ? matched.id : null;
  };

  // 拆分批量文本：按分隔符拆分 → 每段去首尾空格 → 丢弃空段
  const splitBatchText = (text: string) =>
    text
      .split(SEPARATOR_REGEX)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);

  const showDropdown = () => {
    if (!isCandidateMode.value || props.disabled) {
      return;
    }
    if (triggerRef.value) {
      triggerWidth.value = triggerRef.value.offsetWidth;
    }
    tippyInstance?.show();
    nextTick(() => {
      tippyInstance?.popperInstance?.update();
    });
  };

  const hideDropdown = () => {
    tippyInstance?.hide();
  };

  // 选择候选 / 全选 / 回车添加后：清除过滤词。多选下拉保持打开并回到未过滤列表；单选收起
  const resetKeywordKeepOpen = () => {
    inputValue.value = '';
    if (!props.multiple) {
      hideDropdown();
      return;
    }
    showDropdown();
    nextTick(() => {
      inputRef.value?.focus();
    });
  };

  const handleTriggerClick = () => {
    if (props.disabled) {
      return;
    }
    inputRef.value?.focus();
    showDropdown();
  };

  const handleInputFocus = () => {
    isFocus.value = true;
    visibleTagCount.value = modelValue.value.length;
    showDropdown();
  };

  const handleInputBlur = () => {
    // 延时关闭，避免点击候选项（已阻止 mousedown）之外的失焦竞态
    setTimeout(() => {
      isFocus.value = false;
      hideDropdown();
      updateVisibleTagCount();
    }, 200);
  };

  const handleInput = () => {
    showDropdown();
  };

  const handleRemoveTag = (value: string) => {
    removeValue(value);
  };

  const handleClear = () => {
    emitChange([]);
  };

  const handleExpandTags = () => {
    inputRef.value?.focus();
  };

  const handleEnter = () => {
    if (isCandidateMode.value) {
      // 有高亮候选优先添加高亮项（回车不把输入串当自由值）
      if (highlightIndex.value >= 0 && highlightIndex.value < filteredList.value.length) {
        appendValues([filteredList.value[highlightIndex.value].id]);
        resetKeywordKeepOpen();
        return;
      }
      // 无高亮时：允许新建则在回车时按分隔符拆分并创建标签，否则保留输入内容
      const createValues = splitBatchText(inputValue.value);
      if (props.allowCreate && createValues.length) {
        appendValues(createValues);
        resetKeywordKeepOpen();
      }
      return;
    }
    // 自由录入：回车时按分隔符拆分，非空即加
    const values = splitBatchText(inputValue.value);
    if (!values.length) {
      return;
    }
    appendValues(values);
    inputValue.value = '';
  };

  const handleKeydown = (event: KeyboardEvent) => {
    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        handleEnter();
        break;
      case 'Backspace':
        // 输入区无内容时，Backspace 删除最后一个已选标签
        if (!inputValue.value && modelValue.value.length) {
          removeValue(modelValue.value[modelValue.value.length - 1]);
        }
        break;
      case 'ArrowDown':
        if (isCandidateMode.value && filteredList.value.length) {
          event.preventDefault();
          highlightIndex.value = Math.min(filteredList.value.length - 1, highlightIndex.value + 1);
        }
        break;
      case 'ArrowUp':
        if (isCandidateMode.value && filteredList.value.length) {
          event.preventDefault();
          highlightIndex.value = Math.max(0, highlightIndex.value - 1);
        }
        break;
      case 'Escape':
        hideDropdown();
        break;
      default:
        break;
    }
  };

  const handlePaste = (event: ClipboardEvent) => {
    event.preventDefault();
    const text = event.clipboardData?.getData('text') ?? '';
    const segments = splitBatchText(text);
    if (!segments.length) {
      return;
    }

    if (!isCandidateMode.value || props.allowCreate) {
      // 自由录入 / 允许新建：命中候选归一化为候选值，其余原样新建，无忽略提示
      appendValues(segments.map((segment) => resolveCandidateValue(segment) ?? segment));
      inputValue.value = '';
      return;
    }

    // 仅候选：仅保留合法段，统计并提示被忽略的无效值
    const legalValues: string[] = [];
    let invalidCount = 0;
    segments.forEach((segment) => {
      const value = resolveCandidateValue(segment);
      if (value) {
        legalValues.push(value);
      } else {
        invalidCount += 1;
      }
    });
    appendValues(legalValues);
    inputValue.value = '';
    if (invalidCount > 0) {
      Message({
        message: t('已忽略 n 个无效值', { n: invalidCount }),
        theme: 'warning',
      });
    }
  };

  const handleSelectAll = () => {
    const list = filteredList.value;
    if (!list.length) {
      return;
    }
    if (selectAllStatus.value.checked) {
      // 全选态：仅移除当前过滤批中的已选
      const removeSet = new Set(list.map((item) => item.id));
      emitChange(modelValue.value.filter((value) => !removeSet.has(value)));
    } else {
      // 未选 / 半选：并集追加当前过滤全部
      appendValues(list.map((item) => item.id));
    }
    resetKeywordKeepOpen();
  };

  const handleCreate = () => {
    if (!createValue.value) {
      return;
    }
    appendValues([createValue.value]);
    resetKeywordKeepOpen();
  };

  const handleOptionClick = (item: { id: string; name: string }) => {
    // 单选：选中即替换；多选：切换选中态
    if (props.multiple && selectedValueMap.value[item.id]) {
      removeValue(item.id);
    } else {
      appendValues([item.id]);
    }
    resetKeywordKeepOpen();
  };

  onMounted(() => {
    if (triggerRef.value) {
      triggerWidth.value = triggerRef.value.offsetWidth;
      updateVisibleTagCount();
      resizeObserver = new ResizeObserver(([entry]) => {
        triggerWidth.value = entry.contentRect.width;
        updateVisibleTagCount();
        updateDropdownPosition();
      });
      resizeObserver.observe(triggerRef.value);
    }
    if (panelRef.value && dropdownRef.value) {
      tippyInstance = tippy(panelRef.value as SingleTarget, {
        appendTo: () => document.body,
        arrow: false,
        content: dropdownRef.value,
        interactive: true,
        maxWidth: 'none',
        offset: [0, 4],
        placement: 'bottom-start',
        theme: 'db-tag-input',
        trigger: 'manual',
        zIndex: 9999,
      });
    }
  });

  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    resizeObserver = undefined;
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.unmount();
      tippyInstance.destroy();
      tippyInstance = undefined;
    }
  });
</script>

<style lang="less" scoped>
  .db-tag-input {
    position: relative;
    width: 100%;
    height: 32px;
    cursor: text;

    &:hover {
      .db-tag-input-panel {
        border-color: #979ba5;
      }

      .db-tag-input-clear {
        display: block;
      }
    }

    &.is-focus {
      z-index: 10;

      .db-tag-input-panel {
        max-height: none;
        border-color: #3a84ff;
        box-shadow: 0 2px 6px 0 rgb(0 0 0 / 10%);
      }

      .db-tag-input-tag-list {
        flex-wrap: wrap;
        overflow: visible;
      }
    }

    &:not(.is-focus) {
      .db-tag-input-tag {
        max-width: 30%;

        :deep(.bk-tag-text) {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    &.is-disabled {
      cursor: not-allowed;

      .db-tag-input-panel {
        background: #fafbfd;
      }

      .db-tag-input-input {
        cursor: not-allowed;
      }
    }

    .db-tag-input-panel {
      position: absolute;
      top: 0;
      left: 0;
      z-index: 1;
      display: flex;
      width: 100%;
      max-height: 32px;
      min-height: 32px;
      padding: 0 24px 0 4px;
      overflow: hidden;
      background: #fff;
      border: 1px solid #c4c6cc;
      border-radius: 2px;
      align-items: flex-start;
      transition: border-color 0.2s;
    }

    .db-tag-input-tag-list {
      display: flex;
      width: 100%;
      padding: 3px 0;
      overflow: hidden;
      flex-wrap: nowrap;
      gap: 4px;
      align-items: center;
    }

    .db-tag-input-tag {
      margin: 0;
      flex-shrink: 0;
    }

    .db-tag-input-overflow-tag {
      color: #3a84ff;
      cursor: pointer;
    }

    .db-tag-input-input {
      height: 22px;
      min-width: 40px;
      padding: 0 4px;
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      background: transparent;
      border: none;
      outline: none;
      flex: 1;

      &::placeholder {
        color: #c4c6cc;
      }
    }

    .db-tag-input-measure {
      position: fixed;
      top: -9999px;
      left: -9999px;
      display: flex;
      padding: 3px 24px 3px 4px;
      visibility: hidden;
      gap: 4px;
    }

    .db-tag-input-clear {
      position: absolute;
      top: 16px;
      right: 6px;
      display: none;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transform: translateY(-50%);

      &:hover {
        color: #979ba5;
      }
    }
  }
</style>

<style lang="less">
  // tippy 下拉容器：去除默认背景与内边距，样式交由内容区自行控制
  .tippy-box[data-theme~='db-tag-input'] {
    background-color: transparent;

    .tippy-content {
      padding: 0;
    }
  }

  .db-tag-input-dropdown-content {
    max-height: 240px;
    overflow-y: auto;
    font-size: 12px;
    color: #63656e;
    background: #fff;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    box-shadow: 0 2px 6px 0 rgb(0 0 0 / 10%);

    .db-tag-input-option {
      display: flex;
      height: 32px;
      padding: 0 12px;
      cursor: pointer;
      align-items: center;
      gap: 8px;

      &:hover,
      &.is-highlight {
        background: #f5f7fa;
      }

      &.is-selected {
        color: #3a84ff;
        background: #f5f7fa;
      }

      .db-tag-input-option-label {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
      }

      .db-tag-input-option-check {
        font-size: 14px;
        color: #3a84ff;
      }
    }

    .db-tag-input-create {
      color: #3a84ff;

      &:hover {
        background: #f5f7fa;
      }
    }

    .db-tag-input-select-all {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #fff;
      border-bottom: 1px solid #f0f1f5;
    }

    .db-tag-input-empty {
      padding: 12px;
      color: #c4c6cc;
      text-align: center;
    }
  }
</style>
