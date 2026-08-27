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
    @click="handleTriggerClick"
    @mousedown="handleTriggerMousedown">
    <div
      ref="panelRef"
      class="db-tag-input-panel">
      <div
        ref="tagListRef"
        class="db-tag-input-tag-list">
        <DbTag
          v-for="(value, index) in modelValue"
          :key="value"
          class="db-tag-input-tag"
          :closable="!disabled"
          :stop-propagation="false"
          :style="{ display: isTagHidden(index) ? 'none' : '' }"
          @close="handleRemoveTag(value)">
          {{ getValueLabel(value) }}
        </DbTag>
        <DbTag
          v-bk-tooltips="{
            content: collapsedTagTips,
            disabled: !collapsedTagTips,
          }"
          class="db-tag-input-tag db-tag-input-overflow-tag"
          :style="{ display: collapsedTagCount > 0 ? '' : 'none' }"
          @click.stop="handleExpandTags">
          +{{ collapsedTagCount }}
        </DbTag>
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
                'is-selected': !multiple && selectedValueSet.has(item.id),
              }"
              @click="handleOptionClick(item)"
              @mouseenter="highlightIndex = index">
              <BkCheckbox
                v-if="multiple"
                :model-value="selectedValueSet.has(item.id)"
                style="pointer-events: none" />
              <span
                v-overflow-tips
                class="db-tag-input-option-label">
                {{ item.name }}
              </span>
              <DbIcon
                v-if="!multiple && selectedValueSet.has(item.id)"
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
  import { useFormItem } from 'bkui-vue/lib/shared';
  import { debounce } from 'lodash';
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
    /** 值变化 / 失焦时是否触发所在表单项的校验 */
    withValidate?: boolean;
  }

  interface Emits {
    (e: 'change', value: string[]): void;
    (e: 'focus'): void;
    (e: 'blur', value: string, tagList: string[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    allowCreate: false,
    clearable: true,
    contentWidth: undefined,
    disabled: false,
    list: undefined,
    mode: undefined,
    multiple: false,
    placeholder: '',
    withValidate: true,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const formItem = useFormItem();

  const { t } = useI18n();

  // 批量粘贴分隔符：逗号、分号、竖线、换行、制表符、空格（含中文全角），连续分隔符产生空段后统一丢弃
  const SEPARATOR_REGEX = /[,，;；、｜|\t\r\n ]/;

  const triggerRef = useTemplateRef('triggerRef');
  const panelRef = useTemplateRef('panelRef');
  const tagListRef = useTemplateRef('tagListRef');
  const inputRef = useTemplateRef('inputRef');
  const dropdownRef = useTemplateRef('dropdownRef');

  const inputValue = ref('');
  const isFocus = ref(false);
  const highlightIndex = ref(-1);
  const triggerWidth = ref(0);
  // 收起态第一个被折叠的标签下标，null 表示无需折叠
  const overflowTagIndex = ref<number | null>(null);

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

  const isTagHidden = (index: number) =>
    !isFocus.value && overflowTagIndex.value !== null && index >= overflowTagIndex.value;

  const collapsedTagCount = computed(() =>
    isFocus.value || overflowTagIndex.value === null ? 0 : modelValue.value.length - overflowTagIndex.value,
  );

  // 已选值集合，用于去重与选中态判断
  const selectedValueSet = computed(() => new Set(modelValue.value));

  // 候选值展示名映射
  const candidateNameMap = computed(() => new Map(candidateList.value.map((item) => [item.id, item.name])));

  // 关键词包含匹配（不区分大小写，id / 展示名任一命中即可）；多个分隔词按 OR 匹配，无关键词展示全部候选
  const filteredList = computed(() => {
    const keywords = inputValue.value
      .split(SEPARATOR_REGEX)
      .map((item) => item.trim().toLowerCase())
      .filter((item) => item.length > 0);
    if (!keywords.length) {
      return candidateList.value;
    }
    return candidateList.value.filter((item) => {
      const id = item.id.toLowerCase();
      const name = item.name.toLowerCase();
      return keywords.some((keyword) => name.includes(keyword) || id.includes(keyword));
    });
  });

  // 允许新建时，输入词非候选且未选中，则展示「新建」入口
  const createValue = computed(() => {
    if (!props.allowCreate || !isCandidateMode.value) {
      return '';
    }
    const value = inputValue.value.trim();
    if (!value || selectedValueSet.value.has(value)) {
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
    const selectedCount = list.filter((item) => selectedValueSet.value.has(item.id)).length;
    return {
      checked: selectedCount === list.length,
      indeterminate: selectedCount > 0 && selectedCount < list.length,
    };
  });

  /**
   * 计算收起态的折叠位置：先还原全部标签，找出第一个换行的标签作为折叠起点；
   * 若 +N 自身被挤到第二行，则再少展示一个标签。容器过窄时至少保留一个标签。
   */
  const calcOverflow = async () => {
    if (isFocus.value) {
      return;
    }
    overflowTagIndex.value = null;
    await nextTick();
    const tagElements = Array.from(tagListRef.value?.querySelectorAll<HTMLElement>('.db-tag-input-tag') ?? []).filter(
      (element) => !element.classList.contains('db-tag-input-overflow-tag'),
    );
    const firstLineTop = tagElements[0]?.offsetTop;
    const wrappedIndex = tagElements.findIndex((element, index) => index > 0 && element.offsetTop !== firstLineTop);
    if (wrappedIndex <= 0) {
      return;
    }
    overflowTagIndex.value = wrappedIndex;
    await nextTick();
    const overflowTagElement = tagListRef.value?.querySelector<HTMLElement>('.db-tag-input-overflow-tag');
    if (overflowTagElement && overflowTagElement.offsetTop !== firstLineTop && wrappedIndex > 1) {
      overflowTagIndex.value = wrappedIndex - 1;
    }
  };

  const debouncedCalcOverflow = debounce(calcOverflow, 150);

  // 内容变化后重新计算下拉位置
  const updateDropdownPosition = () => {
    if (tippyInstance?.state.isShown) {
      nextTick(() => {
        tippyInstance?.popperInstance?.update();
      });
    }
  };

  /**
   * 重置浏览高亮。
   * 对齐 bk-tag-input：不允许新建时默认高亮首项，回车即可选中；
   * 允许新建时不预选，避免抢走「新建」输入。
   */
  const resetHighlight = () => {
    highlightIndex.value = isCandidateMode.value && !props.allowCreate && filteredList.value.length ? 0 : -1;
  };

  watch(filteredList, () => {
    resetHighlight();
    updateDropdownPosition();
  });

  watch(createValue, () => {
    updateDropdownPosition();
  });

  // 已选值与展示名都会影响标签宽度，两者变化后都要重算折叠位置
  watch([modelValue, candidateNameMap], calcOverflow, {
    deep: true,
    flush: 'post',
  });

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

  const getValueLabel = (value: string) => candidateNameMap.value.get(value) ?? value;

  // 折叠标签的 tooltip：列出被 +N 收起的值
  const collapsedTagTips = computed(() =>
    collapsedTagCount.value > 0
      ? modelValue.value
          .slice(overflowTagIndex.value ?? 0)
          .map((value) => getValueLabel(value))
          .join('、')
      : '',
  );

  const emitChange = (value: string[]) => {
    modelValue.value = value;
    emits('change', value);
    if (props.withValidate) {
      formItem?.validate?.('change');
    }
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
    resetHighlight();
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
  };

  const handleTriggerClick = () => {
    if (props.disabled) {
      return;
    }
    inputRef.value?.focus();
    showDropdown();
  };

  /**
   * 点击组件内非输入框区域（标签、+N、清空、面板空白）时阻止默认的焦点转移。
   * 输入焦点不丢失，blur 便只在焦点真正离开组件时触发，无需延时兜底失焦与重新聚焦的往返。
   * 点击输入框本身不拦截，保留光标定位与拖选。
   */
  const handleTriggerMousedown = (event: MouseEvent) => {
    // 禁用态没有焦点要保住，放行以便选中复制标签文字
    if (props.disabled) {
      return;
    }
    if (event.target !== inputRef.value) {
      event.preventDefault();
    }
  };

  const handleInputFocus = () => {
    isFocus.value = true;
    showDropdown();
    emits('focus');
  };

  /**
   * 失焦时提交残留输入，避免输入完未按回车就点击其他区域导致内容静默丢失。
   * 命中候选的段归一化为候选值；「仅候选」且不允许新建时，非候选段无法成为标签只能丢弃。
   */
  const commitResidualInput = () => {
    const segments = splitBatchText(inputValue.value);
    if (!segments.length) {
      return;
    }
    if (isCandidateMode.value && !props.allowCreate) {
      appendValues(
        segments.map((segment) => resolveCandidateValue(segment)).filter((value): value is string => value !== null),
      );
      return;
    }
    appendValues(segments.map((segment) => resolveCandidateValue(segment) ?? segment));
  };

  const handleInputBlur = () => {
    const residualValue = inputValue.value;
    commitResidualInput();
    inputValue.value = '';
    isFocus.value = false;
    hideDropdown();
    calcOverflow();
    emits('blur', residualValue, modelValue.value);
    if (props.withValidate) {
      formItem?.validate?.('blur');
    }
  };

  const handleInput = () => {
    showDropdown();
  };

  const handleRemoveTag = (value: string) => {
    removeValue(value);
  };

  const handleClear = () => {
    inputValue.value = '';
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
      // 输入内容精确命中候选时直接选中，避免 allowCreate 下创建出与候选重复的自由值
      const matchedValue = resolveCandidateValue(inputValue.value);
      if (matchedValue) {
        appendValues([matchedValue]);
        resetKeywordKeepOpen();
        return;
      }
      // 无高亮时：允许新建则在回车时按分隔符拆分并创建标签，否则保留输入内容
      const createValues = splitBatchText(inputValue.value);
      if (props.allowCreate && createValues.length) {
        // 与粘贴保持一致：命中候选的段归一化为候选值，其余原样新建
        appendValues(createValues.map((segment) => resolveCandidateValue(segment) ?? segment));
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
    if (props.multiple && selectedValueSet.value.has(item.id)) {
      removeValue(item.id);
    } else {
      appendValues([item.id]);
    }
    resetKeywordKeepOpen();
  };

  onMounted(() => {
    calcOverflow();
    if (triggerRef.value) {
      triggerWidth.value = triggerRef.value.offsetWidth;
      resizeObserver = new ResizeObserver(([entry]) => {
        triggerWidth.value = entry.contentRect.width;
        debouncedCalcOverflow();
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
    debouncedCalcOverflow.cancel();
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
        overflow: visible;
      }

      .db-tag-input-input {
        min-width: 40px;
      }
    }

    &:not(.is-focus) {
      .db-tag-input-tag {
        max-width: 30%;
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
      // 收起态靠换行位置识别溢出标签，超出的行由 panel 的 max-height 裁掉
      flex-wrap: wrap;
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
      // 收起态允许压缩到 0，避免输入框把标签挤到第二行
      min-width: 0;
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
