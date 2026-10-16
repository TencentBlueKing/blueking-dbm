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
    ref="rootRef"
    class="dbm-date-picker"
    :class="{
      'is-disabled': disabled,
      'is-focused': opened,
      'is-long': type === 'datetimerange',
      'is-simplicity': behavior === 'simplicity',
    }">
    <div
      ref="triggerRef"
      class="dbm-date-picker-trigger"
      @click="handleTriggerClick"
      @mouseenter="isHover = true"
      @mouseleave="isHover = false">
      <slot
        :display-value="displayValue"
        name="trigger">
        <span
          class="dbm-date-picker-icon"
          @click="handleIconClick">
          <svg viewBox="0 0 1024 1024">
            <path
              d="M896,128h-96v64h64v112H160V192h64v-64h-96c-17.7,0-32,14.3-32,32v736c0,17.7,14.3,32,32,32h768c17.7,0,32-14.3,32-32V160C928,142.3,913.7,128,896,128z M160,864V368h704v496H160z" />
            <rect
              height="64"
              width="192"
              x="416"
              y="128" />
            <rect
              height="128"
              width="64"
              x="288"
              y="96" />
            <rect
              height="128"
              width="64"
              x="672"
              y="96" />
            <polygon
              points="403.7,514.4 557.1,514.4 557.1,515.3 420.1,765.5 483.5,765.5 620.3,504.3 620.3,466.5 403.7,466.5" />
          </svg>
        </span>
        <input
          :key="inputKey"
          ref="inputRef"
          class="dbm-date-picker-input"
          :class="{ 'is-readonly': readonly }"
          :disabled="disabled"
          :placeholder="placeholder"
          :readonly="isInputReadonly"
          type="text"
          :value="displayValue"
          @blur="handleBlur"
          @change="handleInputChange"
          @click="handleInputClick"
          @focus="handleFocus"
          @keydown="handleKeydown" />
        <Close
          v-if="showClear"
          class="dbm-date-picker-clear"
          @click.stop="handleClear" />
      </slot>
    </div>
    <!-- 下拉面板：作为 tippy.js 挂载源，展示时被移动到 body（或组件内部） -->
    <div style="display: none">
      <div
        ref="contentRef"
        class="dbm-date-picker-popover"
        :class="extPopoverCls">
        <!-- 头尾插槽裸渲染，不带样式容器，避免短路插槽渲染出空盒子 -->
        <div
          v-if="$slots.header"
          :class="headerSlotCls">
          <slot name="header" />
        </div>
        <DateRangePanel
          v-if="isRange"
          ref="panelRef"
          :active-shortcut-index="activeShortcutIndex"
          :clearable="clearable"
          :confirm="isConfirm"
          :dates="internalValue"
          :disabled-date="disabledDate"
          :shortcut-close="shortcutClose"
          :shortcuts="shortcuts"
          :show-seconds="showSeconds"
          :show-time="showTime"
          :start-date="startDate"
          @pick="handlePick"
          @pick-clear="handleClear"
          @pick-first="(date: Date) => emits('pick-first', date)"
          @pick-success="handlePickSuccess" />
        <DatePanel
          v-else
          ref="panelRef"
          :active-shortcut-index="activeShortcutIndex"
          :clearable="clearable"
          :confirm="isConfirm"
          :dates="internalValue"
          :disabled-date="disabledDate"
          :selection-mode="selectionMode"
          :shortcut-close="shortcutClose"
          :shortcuts="shortcuts"
          :show-seconds="showSeconds"
          :show-time="showTime"
          :start-date="startDate"
          @pick="handlePick"
          @pick-clear="handleClear"
          @pick-success="handlePickSuccess" />
        <div
          v-if="$slots.footer"
          :class="footerSlotCls">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Close } from 'bkui-vue/lib/icon';
  import { useFormItem } from 'bkui-vue/lib/shared';
  import tippy, { type Instance, type Placement, type SingleTarget } from 'tippy.js';
  import type { VNode } from 'vue';

  import {
    type DatePickerShortcut,
    type DatePickerType,
    DEFAULT_FORMATS,
    type DisabledDate,
    formatDate,
    formatValue,
    getSelectionMode,
    getShortcutValue,
    type InternalValue,
    isRangeType,
    parseInputText,
    parseValue,
    type PickerValue,
    type PickOptions,
  } from './common';
  import DatePanel from './components/DatePanel.vue';
  import DateRangePanel from './components/DateRangePanel.vue';

  interface Props {
    appendToBody?: boolean;
    behavior?: 'normal' | 'simplicity';
    clearable?: boolean;
    disabled?: boolean;
    disabledDate?: DisabledDate;
    /** 是否允许手动输入 */
    editable?: boolean;
    extPopoverCls?: string;
    footerSlotCls?: string;
    /** dayjs 格式写法，如 YYYY-MM-DD HH:mm:ss；不传按 type 取默认值 */
    format?: string;
    headerSlotCls?: string;
    /** 受控展开状态，传入后展开 / 收起完全由外部控制 */
    open?: boolean;
    placeholder?: string;
    placement?: Placement;
    readonly?: boolean;
    /** 点击快捷项后收起面板 */
    shortcutClose?: boolean;
    shortcuts?: DatePickerShortcut[];
    /** 初始选中的快捷项下标 */
    shortcutSelectedIndex?: number;
    /** 面板默认展示的月份 */
    startDate?: Date;
    type?: DatePickerType;
    /** 选中快捷项时输入框展示快捷项文案 */
    useShortcutText?: boolean;
    /** 兼容 bk-date-picker 的 :value 写法，优先使用 v-model */
    value?: PickerValue;
    withValidate?: boolean;
  }

  // change 的 value 声明为 any，与原 bk-date-picker 运行时 emits 的类型表现对齐，避免业务侧处理器参数逆变报错
  interface Emits {
    (e: 'change', value: any, type: string): void;
    (e: 'blur' | 'clear' | 'focus' | 'pick-success'): void;
    (e: 'open-change', visible: boolean): void;
    (e: 'pick-first', date: Date): void;
    (e: 'shortcut-change', shortcut: DatePickerShortcut | undefined, index: number): void;
  }

  interface Exposes {
    focus: () => void;
  }

  defineOptions({
    name: 'DatePicker',
  });

  const props = withDefaults(defineProps<Props>(), {
    appendToBody: false,
    behavior: 'normal',
    clearable: true,
    disabled: false,
    disabledDate: undefined,
    editable: true,
    extPopoverCls: '',
    footerSlotCls: '',
    format: undefined,
    headerSlotCls: '',
    open: undefined,
    placeholder: '',
    placement: 'bottom-start',
    readonly: false,
    shortcutClose: false,
    shortcuts: () => [],
    shortcutSelectedIndex: -1,
    startDate: undefined,
    type: 'date',
    useShortcutText: false,
    value: undefined,
    withValidate: true,
  });

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    footer?: () => VNode;
    header?: () => VNode;
    trigger?: (props: { displayValue: string }) => VNode;
  }>();

  // 与 bk-date-picker 一致：v-model 回写 Date（范围为 Date 数组，空值为 ''），change 抛出按 format 格式化的字符串
  const modelValue = defineModel<PickerValue>({
    default: undefined,
  });

  const formItem = useFormItem();

  const rootRef = useTemplateRef('rootRef');
  const triggerRef = useTemplateRef('triggerRef');
  const inputRef = useTemplateRef('inputRef');
  const contentRef = useTemplateRef('contentRef');
  const panelRef = ref<{ reset: () => void } | null>(null);

  let tippyInstance: Instance | undefined;
  let resizeObserver: ResizeObserver | undefined;

  const isRange = computed(() => isRangeType(props.type));
  const localFormat = computed(() => props.format || DEFAULT_FORMATS[props.type]);
  const selectionMode = computed(() => getSelectionMode(props.type));
  const showTime = computed(() => props.type === 'datetime' || props.type === 'datetimerange');
  // 与 bk-date-picker 一致：format 以分钟结尾时时间面板不展示秒
  const showSeconds = computed(() => !/mm$/.test(localFormat.value));
  // 带时间或自定义触发器时，选中后不自动收起，由确认栏或外部收起
  const isConfirm = computed(() => showTime.value || !!slots.trigger);

  // 指定了初始快捷项时，以快捷项的值作为初始值
  const getInitialState = () => {
    const shortcut = props.shortcuts[props.shortcutSelectedIndex];
    const shortcutValue = getShortcutValue(shortcut);
    if (shortcutValue) {
      return {
        dates: Array.isArray(shortcutValue) ? [...shortcutValue] : [shortcutValue],
        shortcut,
      };
    }
    return {
      dates: parseValue(modelValue.value ?? props.value, props.type, localFormat.value),
      shortcut: undefined,
    };
  };

  const initialState = getInitialState();

  const internalValue = ref<InternalValue>(initialState.dates);
  const currentShortcut = shallowRef<DatePickerShortcut | undefined>(initialState.shortcut);
  // 受控模式下 visible 记录组件内部的展开意图（点外部、确定等会置为 false），通过 open-change 通知外部
  const visible = ref(props.open === true);
  const isHover = ref(false);
  // 手动输入不合法时自增，强制重建输入框以还原展示值
  const inputKey = ref(0);

  const opened = computed(() => props.open ?? visible.value);

  const activeShortcutIndex = computed(() =>
    currentShortcut.value ? props.shortcuts.indexOf(currentShortcut.value) : -1,
  );

  const displayValue = computed(() => {
    if (props.useShortcutText && currentShortcut.value?.text) {
      return currentShortcut.value.text;
    }
    return formatValue(internalValue.value, props.type, localFormat.value);
  });

  // 展示快捷项文案时输入内容不是合法日期，不允许编辑
  const isInputReadonly = computed(
    () => props.readonly || !props.editable || (props.useShortcutText && !!currentShortcut.value?.text),
  );

  const showClear = computed(
    () => props.clearable && isHover.value && !props.disabled && !props.readonly && !!displayValue.value,
  );

  const getModelValue = (): PickerValue => {
    const values = internalValue.value.map((date) => (date ? new Date(date) : ''));
    return isRange.value ? values : values[0];
  };

  const getStringValue = () => {
    const values = internalValue.value.map((date) => formatDate(date, localFormat.value));
    return isRange.value ? values : values[0];
  };

  const emitChange = (type: string) => {
    nextTick(() => {
      modelValue.value = getModelValue();
      emits('change', getStringValue(), type);
      // 与 bk-date-picker 一致：带时间的类型仍在面板内操作，不主动失焦
      if (!showTime.value) {
        inputRef.value?.blur();
      }
    });
  };

  const handlePick = (dates: InternalValue, options: PickOptions) => {
    internalValue.value = dates;
    if (!isConfirm.value) {
      visible.value = !!options.keepOpen;
    }
    currentShortcut.value = options.shortcut;
    emitChange(options.type);
    emits('shortcut-change', options.shortcut, activeShortcutIndex.value);
  };

  const handlePickSuccess = () => {
    visible.value = false;
    // 放到 nextTick，保证外部收到 pick-success 时 v-model 已更新
    nextTick(() => {
      emits('pick-success');
    });
    inputRef.value?.blur();
  };

  const handleClear = () => {
    visible.value = false;
    internalValue.value = internalValue.value.map(() => null);
    currentShortcut.value = undefined;
    emits('clear');
    emitChange(props.type);
  };

  const handleInputClick = () => {
    if (props.disabled || props.readonly) {
      return;
    }
    visible.value = true;
  };

  const handleIconClick = () => {
    if (props.disabled) {
      return;
    }
    inputRef.value?.focus();
    handleInputClick();
  };

  // 自定义触发器没有输入框，点击触发器区域展开
  const handleTriggerClick = () => {
    if (!slots.trigger || props.disabled) {
      return;
    }
    visible.value = true;
  };

  const handleFocus = () => {
    emits('focus');
  };

  const handleBlur = () => {
    emits('blur');
    // 面板展开时失焦（如点击面板）不校验，收起时再校验
    if (opened.value) {
      return;
    }
    if (props.withValidate) {
      formItem?.validate?.('blur');
    }
  };

  const handleKeydown = (event: KeyboardEvent) => {
    if ((event.key === 'Escape' || event.key === 'Tab') && opened.value) {
      event.stopPropagation();
      visible.value = false;
    }
  };

  // 手动输入：按 format 严格解析，合法且未被禁用才生效，否则还原为原展示值
  const handleInputChange = (event: Event) => {
    const text = (event.target as HTMLInputElement).value.trim();
    const dates = parseInputText(text, props.type, localFormat.value);
    const isDisabled = !!dates && !!props.disabledDate && dates.some((date) => date && props.disabledDate!(date));
    if (dates && !isDisabled && text !== displayValue.value) {
      internalValue.value = dates;
      currentShortcut.value = undefined;
      emitChange(props.type);
      return;
    }
    inputKey.value += 1;
  };

  // 用 mousedown + composedPath 判断点击外部：面板内切换年/月表格时被点击的节点会被移除，click 阶段已无法用 contains 判断
  const handleDocumentMousedown = (event: MouseEvent) => {
    const path = event.composedPath();
    if ((rootRef.value && path.includes(rootRef.value)) || (tippyInstance && path.includes(tippyInstance.popper))) {
      return;
    }
    visible.value = false;
  };

  const syncValue = (value: PickerValue) => {
    internalValue.value = parseValue(value, props.type, localFormat.value);
    if (props.withValidate) {
      formItem?.validate?.('change');
    }
  };

  // v-model 与 :value 分开监听，谁变按谁解析：未绑 v-model 时本地 model 会被 emitChange 写入，合并取值会让后续 :value 失效
  watch(modelValue, syncValue);

  watch(() => props.value, syncValue);

  watch(
    () => props.open,
    (open) => {
      visible.value = open === true;
    },
  );

  // 与 bk-date-picker 一致：open-change 跟随内部展开状态，受控模式下外部据此回写 open
  watch(visible, (isVisible) => {
    emits('open-change', isVisible);
  });

  watch(opened, (isOpened) => {
    if (isOpened) {
      tippyInstance?.show();
      document.addEventListener('mousedown', handleDocumentMousedown);
      return;
    }
    tippyInstance?.hide();
    document.removeEventListener('mousedown', handleDocumentMousedown);
    if (props.withValidate) {
      formItem?.validate?.('blur');
    }
  });

  onMounted(() => {
    if (!triggerRef.value || !contentRef.value) {
      return;
    }
    tippyInstance = tippy(triggerRef.value as SingleTarget, {
      appendTo: () => (props.appendToBody ? document.body : (rootRef.value ?? document.body)),
      arrow: false,
      content: contentRef.value,
      hideOnClick: false,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 4],
      // 收起动画结束后再重置面板视图，避免收起过程中面板内容跳动
      onHidden: () => panelRef.value?.reset(),
      placement: props.placement,
      theme: 'dbm-date-picker',
      trigger: 'manual',
      zIndex: 9999,
    });
    // 切换时间面板、快捷项等导致面板尺寸变化时重新定位
    resizeObserver = new ResizeObserver(() => {
      tippyInstance?.popperInstance?.update();
    });
    resizeObserver.observe(contentRef.value);
    if (opened.value) {
      tippyInstance.show();
      document.addEventListener('mousedown', handleDocumentMousedown);
    }
  });

  onBeforeUnmount(() => {
    document.removeEventListener('mousedown', handleDocumentMousedown);
    resizeObserver?.disconnect();
    resizeObserver = undefined;
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.unmount();
      tippyInstance.destroy();
      tippyInstance = undefined;
    }
  });

  defineExpose<Exposes>({
    focus: handleIconClick,
  });
</script>

<style lang="less">
  .dbm-date-picker {
    position: relative;
    display: inline-block;
    width: 261px;
    font-size: 12px;
    line-height: normal;
    color: #63656e;
    vertical-align: middle;

    &.is-long {
      width: 342px;
    }

    .dbm-date-picker-trigger {
      position: relative;
    }

    .dbm-date-picker-icon {
      position: absolute;
      top: 0;
      left: 0;
      display: flex;
      width: 32px;
      height: 100%;
      cursor: pointer;
      align-items: center;
      justify-content: center;

      svg {
        width: 18px;
        height: 18px;
        fill: #c4c6cc;
      }
    }

    .dbm-date-picker-input {
      display: block;
      width: 100%;
      height: 32px;
      padding: 0 10px 0 30px;
      font-size: 12px;
      line-height: 32px;
      color: #63656e;
      cursor: pointer;
      background-color: #fff;
      border: 1px solid #c4c6cc;
      border-radius: 2px;
      outline: none;
      box-sizing: border-box;
      transition: border-color 0.2s;

      &::placeholder {
        color: #c4c6cc;
      }

      &:hover {
        border-color: #979ba5;
      }

      &:focus {
        border-color: #3a84ff;
      }

      &.is-readonly {
        cursor: default;
        background-color: #fafbfd;
        border-color: #dcdee5;
      }

      &[disabled] {
        color: #c4c6cc;
        cursor: not-allowed;
        background-color: #fafbfd;
        border-color: #dcdee5;
      }
    }

    .dbm-date-picker-clear {
      position: absolute;
      top: 50%;
      right: 10px;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      background-color: #fff;
      transform: translateY(-50%);

      &:hover {
        color: #979ba5;
      }
    }

    &.is-focused {
      .dbm-date-picker-input {
        border-color: #3a84ff;
      }
    }

    &.is-disabled {
      .dbm-date-picker-icon {
        cursor: not-allowed;
      }
    }

    &.is-simplicity {
      .dbm-date-picker-input {
        background-color: transparent;
        border-color: transparent transparent #c4c6cc;
        border-radius: 0;

        &:focus {
          border-bottom-color: #3a84ff;
        }
      }

      &.is-focused {
        .dbm-date-picker-input {
          border-color: transparent transparent #3a84ff;
        }
      }
    }
  }

  // tippy 下拉容器：去除默认背景与内边距，样式交由面板自行控制
  .tippy-box[data-theme~='dbm-date-picker'] {
    background-color: transparent;

    .tippy-content {
      padding: 0;
    }
  }

  .dbm-date-picker-popover {
    overflow: hidden;
    font-size: 12px;
    line-height: normal;
    color: #63656e;
    background-color: #fff;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    box-shadow: 0 3px 10px rgb(0 0 0 / 10%);

    .dbm-date-picker-panel {
      position: relative;
      user-select: none;

      &.has-sidebar {
        padding-right: 140px;
      }
    }

    .dbm-date-picker-panel-body {
      width: 261px;
    }

    .dbm-date-picker-panel.is-range {
      .dbm-date-picker-panel-body {
        width: 522px;
      }
    }

    .dbm-date-picker-range-content {
      display: flex;
    }

    .dbm-date-picker-range-item {
      width: 261px;
      flex-shrink: 0;
    }

    .dbm-date-picker-range-item + .dbm-date-picker-range-item {
      border-left: 1px solid #dcdee5;
    }

    .dbm-date-picker-panel-header,
    .dbm-date-picker-time-header {
      height: 46px;
      padding: 0 10px;
      font-size: 14px;
      font-weight: 700;
      line-height: 46px;
      text-align: center;
      border-bottom: 1px solid #dcdee5;
    }

    .dbm-date-picker-panel-header-btn {
      display: inline-flex;
      width: 20px;
      height: 46px;
      font-size: 20px;
      font-weight: normal;
      color: #979ba5;
      cursor: pointer;
      transition: color 0.2s ease-in-out;
      align-items: center;
      justify-content: center;

      &:hover {
        color: #3a84ff;
      }

      &.is-prev {
        float: left;
      }

      &.is-next {
        float: right;
      }
    }

    .dbm-date-picker-panel-header-label {
      cursor: pointer;

      &:hover {
        color: #3a84ff;
      }
    }

    .dbm-date-picker-date-table,
    .dbm-date-picker-period-table {
      display: flex;
      margin: 9px;
      flex-wrap: wrap;
    }

    .dbm-date-picker-period-table {
      margin-top: 7px;
    }

    .dbm-date-picker-date-table-header {
      display: flex;
      width: 100%;

      span {
        width: 34px;
        height: 26px;
        margin: 3px 0;
        line-height: 26px;
        text-align: center;
      }
    }

    .dbm-date-picker-cell {
      position: relative;
      width: 34px;
      height: 32px;
      line-height: 32px;
      text-align: center;
      cursor: pointer;

      em {
        position: relative;
        z-index: 1;
        display: block;
        width: 100%;
        height: 100%;
        font-style: normal;
      }

      &:hover em {
        background-color: #f0f1f5;
      }

      &.is-other-month em {
        color: #c4c6cc;
      }

      &.is-other-month:hover em {
        background-color: transparent;
      }

      &.is-today em {
        color: #3a84ff;
        box-shadow: 0 0 0 1px #a3c5fd inset;
      }

      &.is-range::before {
        position: absolute;
        inset: 0;
        background-color: #e1ecff;
        content: '';
      }

      &.is-selected em {
        color: #fff;
        background-color: #3a84ff;
        box-shadow: 0 0 0 1px #3a84ff inset;
      }

      &.is-disabled {
        color: #c4c6cc;
        cursor: not-allowed;
        background-color: #f0f1f5;

        em {
          color: inherit;
          background-color: inherit;
        }
      }

      &.is-disabled.is-selected em {
        color: #f7f7f7;
        background-color: #c4c6cc;
      }
    }

    .dbm-date-picker-period-table .dbm-date-picker-cell {
      width: 36px;
      margin: 10px 12px;

      em {
        border-radius: 3px;
      }
    }

    .dbm-date-picker-time-titles {
      display: flex;
      height: 42px;
      font-size: 14px;
      font-weight: 700;
      line-height: 42px;
    }

    .dbm-date-picker-time-title {
      text-align: center;
      flex: 1;
    }

    .dbm-date-picker-time-body {
      position: relative;
      display: flex;
      height: 200px;
    }

    .dbm-date-picker-time-highlight {
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
      z-index: 1;
      height: 32px;
      pointer-events: none;
      background-color: rgb(58 132 255 / 16%);
    }

    .dbm-date-picker-time-list {
      height: 100%;
      overflow-y: auto;
      flex: 1;
      scrollbar-width: none;

      &::-webkit-scrollbar {
        display: none;
      }

      ul {
        // 留出一屏减一行的底部空白，保证最后一项也能滚到高亮条位置
        padding: 0 0 168px;
        margin: 0;
        list-style: none;
      }
    }

    .dbm-date-picker-time-cell {
      height: 32px;
      line-height: 32px;
      text-align: center;
      cursor: pointer;

      &:hover,
      &.is-selected {
        color: #3a84ff;
      }

      &.is-disabled {
        color: #c4c6cc;
        cursor: not-allowed;
      }
    }

    .dbm-date-picker-confirm {
      display: flex;
      height: 42px;
      padding: 0 20px;
      background-color: #fafbfd;
      border-top: 1px solid #dcdee5;
      align-items: center;
      justify-content: flex-end;
    }

    .dbm-date-picker-confirm-time {
      margin-right: auto;
      color: #3a84ff;
      cursor: pointer;

      &.is-disabled {
        color: #c4c6cc;
        cursor: not-allowed;
      }
    }

    .dbm-date-picker-confirm-btn {
      margin-left: 10px;
      color: #979ba5;
      cursor: pointer;

      &.is-primary {
        color: #3a84ff;
      }
    }

    // 侧栏绝对定位，高度跟随面板，快捷项过多时内部滚动
    .dbm-date-picker-shortcuts {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      width: 140px;
      padding: 12px 0;
      overflow-y: auto;
      background-color: #fafbfd;
      border-left: 1px solid #dcdee5;
      box-sizing: border-box;
    }

    .dbm-date-picker-shortcut {
      height: 32px;
      padding: 0 20px;
      overflow: hidden;
      line-height: 32px;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;

      &:hover {
        background-color: #f5f7fa;
      }

      &.is-active {
        color: #3a84ff;
        background-color: #e1ecff;
      }
    }
  }
</style>
