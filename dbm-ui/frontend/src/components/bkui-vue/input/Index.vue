<template>
  <div
    v-if="type === 'textarea'"
    class="dbm-textarea"
    :class="{
      'is-disabled': disabled,
      'is-focused': isFocused,
      'is-readonly': readonly,
      'is-resizable': resize,
    }">
    <textarea
      ref="inputRef"
      :disabled="disabled"
      :maxlength="maxlength"
      :placeholder="placeholder"
      :readonly="readonly"
      :rows="rows"
      :value="modelValue"
      @blur="handleBlur"
      @change="handleChange"
      @compositionend="handleCompositionEnd"
      @compositionstart="handleCompositionStart"
      @focus="handleFocus"
      @input="handleInput"
      @keydown="handleKeydown"
      @keyup="handleKeyup"
      @paste="handlePaste" />
    <span
      v-if="showClear"
      class="dbm-textarea-clear-icon"
      :class="{ 'is-show-clear-only-hover': showClearOnlyHover }"
      @click="handleClear"
      @mousedown.prevent>
      <Close />
    </span>
    <span
      v-if="showCounter"
      class="dbm-textarea-max-length"
      :class="{ 'is-over-limit': isOverLimit }">
      {{ currentLength }} / <span>{{ maxlength }}</span>
    </span>
  </div>
  <div
    v-else
    class="dbm-input"
    :class="{
      'is-disabled': disabled,
      'is-focused': isFocused,
      'is-large': size === 'large',
      'is-readonly': readonly,
      'is-simplicity': behavior === 'simplicity',
      'is-small': size === 'small',
    }">
    <div
      v-if="$slots.prefix || prefix"
      class="dbm-input-prefix-area">
      <slot name="prefix">{{ prefix }}</slot>
    </div>
    <input
      ref="inputRef"
      class="dbm-input-text"
      :disabled="disabled"
      :maxlength="maxlength"
      :placeholder="placeholder"
      :readonly="readonly"
      :type="nativeType"
      :value="modelValue"
      @blur="handleBlur"
      @change="handleChange"
      @compositionend="handleCompositionEnd"
      @compositionstart="handleCompositionStart"
      @focus="handleFocus"
      @input="handleInput"
      @keydown="handleKeydown"
      @keyup="handleKeyup"
      @paste="handlePaste" />
    <span
      v-if="showClear"
      class="dbm-input-suffix-icon dbm-input-clear-icon"
      :class="{ 'is-show-clear-only-hover': showClearOnlyHover }"
      @click="handleClear"
      @mousedown.prevent>
      <Close />
    </span>
    <span
      v-if="type === 'search'"
      class="dbm-input-suffix-icon"
      @click="handleSearch">
      <Search />
    </span>
    <span
      v-else-if="type === 'password'"
      class="dbm-input-suffix-icon"
      @click="handlePasswordVisibleChange">
      <Eye v-if="pwdVisible" />
      <Unvisible v-else />
    </span>
    <span
      v-if="showCounter"
      class="dbm-input-max-length"
      :class="{ 'is-over-limit': isOverLimit }">
      {{ currentLength }} / <span>{{ maxlength }}</span>
    </span>
    <div
      v-if="type === 'number' && showControl"
      class="dbm-input-number-control">
      <span
        :class="{ 'is-disabled': maxDisabled }"
        @click="handleControlClick(1)"
        @mousedown.prevent>
        <DownSmall />
      </span>
      <span
        :class="{ 'is-disabled': minDisabled }"
        @click="handleControlClick(-1)"
        @mousedown.prevent>
        <DownSmall />
      </span>
    </div>
    <div
      v-if="$slots.suffix || suffix"
      class="dbm-input-suffix-area">
      <slot name="suffix">{{ suffix }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Close, DownSmall, Eye, Search, Unvisible } from 'bkui-vue/lib/icon';
  import { useFormItem } from 'bkui-vue/lib/shared';
  import { computed, ref, type VNode, watch } from 'vue';

  interface Props {
    allowEmptyValue?: boolean;
    behavior?: 'normal' | 'simplicity';
    clearable?: boolean;
    disabled?: boolean;
    max?: number;
    maxlength?: number;
    min?: number;
    placeholder?: string;
    precision?: number;
    prefix?: string;
    readonly?: boolean;
    resize?: boolean;
    rows?: number;
    showClearOnlyHover?: boolean;
    showControl?: boolean;
    showWordLimit?: boolean;
    size?: 'small' | 'default' | 'large';
    step?: number;
    suffix?: string;
    type?: 'text' | 'number' | 'textarea' | 'search' | 'password';
    withValidate?: boolean;
  }

  defineOptions({
    name: 'Input',
  });

  const props = withDefaults(defineProps<Props>(), {
    allowEmptyValue: true,
    behavior: 'normal',
    clearable: false,
    disabled: false,
    max: Infinity,
    maxlength: undefined,
    min: -Infinity,
    placeholder: '',
    precision: 0,
    prefix: '',
    readonly: false,
    resize: true,
    rows: 2,
    showClearOnlyHover: true,
    showControl: true,
    showWordLimit: false,
    size: 'default',
    step: 1,
    suffix: '',
    type: 'text',
    withValidate: true,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    prefix?: () => VNode;
    suffix?: () => VNode;
  }>();

  const modelValue = defineModel<string | number>({
    default: '',
  });

  const formItem = useFormItem();

  watch(modelValue, () => {
    if (props.withValidate) {
      formItem?.validate?.('change');
    }
  });

  // value 声明为 any，与原 bk-input 运行时 emits 的类型表现对齐，避免业务侧处理器参数逆变报错
  interface Emits {
    (e: 'input' | 'change', value: any, event?: Event): void;
    (e: 'focus' | 'blur', event: FocusEvent): void;
    (e: 'clear'): void;
    (e: 'enter' | 'keydown' | 'keyup', value: any, event: KeyboardEvent): void;
    (e: 'paste', value: any, event: ClipboardEvent): void;
    (e: 'search', event: MouseEvent): void;
  }

  interface Exposes {
    blur(): void;
    focus(): void;
  }

  const inputRef = ref<HTMLInputElement | HTMLTextAreaElement>();
  const isFocused = ref(false);
  const isComposing = ref(false);
  const pwdVisible = ref(false);

  const nativeType = computed(() => (props.type === 'password' && pwdVisible.value ? 'text' : props.type));

  const currentLength = computed(() => String(modelValue.value ?? '').length);

  const showClear = computed(() => props.clearable && !props.disabled && !props.readonly && !!modelValue.value);

  // 与 bk-input 对齐：textarea 设置 maxlength 即显示字数统计，其他类型需开启 showWordLimit
  const showCounter = computed(
    () => (props.showWordLimit || props.type === 'textarea') && props.maxlength !== undefined,
  );

  const isOverLimit = computed(() => props.maxlength !== undefined && currentLength.value > props.maxlength);

  // 到达边界才禁用箭头，未达边界时点击由 clampNumber 收敛到边界；空值按 0 处理，与 handleControlClick 一致
  const minDisabled = computed(() => props.disabled || props.readonly || Number(modelValue.value) <= props.min);

  const maxDisabled = computed(() => props.disabled || props.readonly || Number(modelValue.value) >= props.max);

  // 数字输入框空值处理：默认取 min（未设置 min 时为 0），allowEmptyValue 时允许为空
  const getNumberEmptyValue = () => {
    if (props.allowEmptyValue) {
      return '';
    }
    return props.min !== -Infinity ? props.min : 0;
  };

  const toPrecision = (num: number) => Number(num.toFixed(props.precision));

  const clampNumber = (value: string) => {
    if (value === '') {
      return getNumberEmptyValue();
    }
    const num = Number(value);
    if (Number.isNaN(num)) {
      return getNumberEmptyValue();
    }
    return Math.min(Math.max(toPrecision(num), props.min), props.max);
  };

  const getInputValue = (event: Event) => (event.target as HTMLInputElement).value.trim();

  // 修正后的值与 modelValue 相同时 vue 不会更新 DOM，需手动同步避免输入框显示与实际值不一致
  const syncNativeValue = (value: string | number) => {
    if (inputRef.value) {
      inputRef.value.value = String(value);
    }
  };

  const handleInput = (event: Event) => {
    if (isComposing.value) {
      return;
    }
    const rawValue = getInputValue(event);
    let value: string | number = rawValue;
    if (props.type === 'number') {
      if (rawValue === '') {
        value = getNumberEmptyValue();
        syncNativeValue(value);
      } else {
        value = toPrecision(Number(rawValue));
      }
    }
    modelValue.value = value;
    emits('input', value, event);
  };

  const handleChange = (event: Event) => {
    const rawValue = getInputValue(event);
    let value: string | number = rawValue;
    if (props.type === 'number') {
      value = clampNumber(rawValue);
      syncNativeValue(value);
    }
    modelValue.value = value;
    emits('change', value, event);
  };

  const handleFocus = (event: FocusEvent) => {
    isFocused.value = true;
    emits('focus', event);
  };

  const handleBlur = (event: FocusEvent) => {
    isFocused.value = false;
    emits('blur', event);
    if (props.withValidate) {
      formItem?.validate?.('blur');
    }
  };

  const handleClear = () => {
    if (props.disabled) {
      return;
    }
    const value = props.type === 'number' ? getNumberEmptyValue() : '';
    modelValue.value = value;
    syncNativeValue(value);
    emits('input', value);
    emits('change', value);
    emits('clear');
  };

  const handleKeydown = (event: KeyboardEvent) => {
    // 跳过输入法组合过程，避免确认候选词的回车被当成提交
    if (isComposing.value || event.isComposing) {
      return;
    }
    const rawValue = getInputValue(event);
    emits('keydown', rawValue, event);
    if (event.key === 'Enter') {
      const value = props.type === 'number' ? clampNumber(rawValue) : rawValue;
      modelValue.value = value;
      emits('enter', value, event);
    }
  };

  const handleKeyup = (event: KeyboardEvent) => {
    if (isComposing.value || event.isComposing) {
      return;
    }
    emits('keyup', getInputValue(event), event);
  };

  const handlePaste = (event: ClipboardEvent) => {
    emits('paste', getInputValue(event), event);
  };

  const handleSearch = (event: MouseEvent) => {
    if (props.disabled) {
      return;
    }
    emits('search', event);
  };

  const handlePasswordVisibleChange = () => {
    pwdVisible.value = !pwdVisible.value;
  };

  const handleCompositionStart = () => {
    isComposing.value = true;
  };

  const handleCompositionEnd = (event: Event) => {
    isComposing.value = false;
    handleInput(event);
  };

  const handleControlClick = (direction: 1 | -1) => {
    if (direction === 1 ? maxDisabled.value : minDisabled.value) {
      return;
    }
    const current = Number(modelValue.value) || 0;
    const value = clampNumber(String(current + direction * props.step));
    modelValue.value = value;
    emits('change', value);
  };

  defineExpose<Exposes>({
    blur() {
      inputRef.value?.blur();
    },
    focus() {
      inputRef.value?.focus();
    },
  });
</script>

<style lang="less">
  @import 'bkui-vue/lib/styles/themes/themes.less';

  .dbm-input,
  .dbm-textarea {
    display: inline-flex;
    width: 100%;
    font-size: 12px;
    color: @default-color;
    background-color: #fff;
    border: 1px solid @light-gray;
    border-radius: 2px;
    box-sizing: border-box;
    transition: all 0.3s;

    ::placeholder {
      font-size: 12px;
      color: @light-gray;
    }

    &.is-disabled,
    &.is-readonly {
      background-color: @input-disabled-bg;
      border-color: @disable-color;

      input,
      textarea {
        color: @gray-color;
        cursor: not-allowed;
        background-color: @input-disabled-bg;
      }
    }

    &.is-readonly {
      input,
      textarea {
        cursor: auto;
      }
    }
  }

  .dbm-input {
    align-items: stretch;
    height: 32px;

    &:hover:not(.is-disabled) {
      border-color: @gray-color;

      .is-show-clear-only-hover {
        display: flex;
      }
    }

    &.is-focused:not(.is-readonly) {
      border-color: @primary-color;
      outline: 0;
      box-shadow: 0 0 3px 0 @input-shadow-color;

      &.is-simplicity {
        border-color: transparent;
        border-bottom-color: @primary-color;
        box-shadow: none;
      }
    }

    &.is-simplicity {
      background-color: transparent;
      border-color: transparent;
      border-bottom-color: @light-gray;

      &:hover:not(.is-disabled) {
        background-color: @input-block-color;
        border-color: transparent;
        border-bottom-color: @gray-color;
        box-shadow: none;

        .dbm-input-text,
        .dbm-input-suffix-icon {
          background-color: @input-block-color;
        }
      }
    }

    &.is-small {
      height: 26px;
    }

    &.is-large {
      height: 40px;
      font-size: 14px;

      ::placeholder {
        font-size: 14px;
      }
    }

    .dbm-input-text {
      flex: 1;
      width: 100%;
      padding: 0 8px;
      overflow: hidden;
      line-height: 1;
      color: @default-color;
      text-overflow: ellipsis;
      white-space: nowrap;
      background-color: #fff;
      background-image: none;
      border: none;
      border-radius: 2px;
      outline: none;
      box-sizing: border-box;
      transition: all 0.3s;

      &[type='search']::-webkit-search-decoration,
      &[type='search']::-webkit-search-cancel-button {
        appearance: none;
      }

      &[type='number']::-webkit-inner-spin-button,
      &[type='number']::-webkit-outer-spin-button {
        margin: 0;
        appearance: none;
      }
    }

    .dbm-input-prefix-area,
    .dbm-input-suffix-area {
      display: flex;
      padding: 0 8px;
      color: @default-color;
      background-color: @input-block-color;
      border-right: 1px solid @light-gray;
      align-items: center;
    }

    .dbm-input-suffix-area {
      border: 0;
      border-left: 1px solid @light-gray;
    }

    .dbm-input-suffix-icon {
      display: flex;
      height: 100%;
      padding-right: 8px;
      font-size: 14px;
      color: @light-gray;
      cursor: pointer;
      background-color: #fff;
      flex-shrink: 0;
      align-items: center;
      align-self: center;

      &:hover {
        color: @gray-color;
      }

      &.is-show-clear-only-hover {
        display: none;
      }
    }

    .dbm-input-max-length {
      padding-right: 8px;
      font-size: 12px;
      transform: scale(0.8);
      align-self: center;

      &.is-over-limit {
        color: @danger-color;
      }

      span {
        color: @input-maxlength-color;
      }
    }

    .dbm-input-number-control {
      display: flex;
      width: 26px;
      height: 100%;
      padding: 4px 0;
      user-select: none;
      flex-direction: column;
      align-items: center;

      // 图标组件自身渲染为 span，必须限定直接子元素，否则内层图标会覆盖箭头的禁用色与光标
      > span {
        display: flex;
        overflow: hidden;
        line-height: 1;
        color: @gray-color;
        text-align: center;
        cursor: pointer;
        background-color: @input-block-color;
        flex: 1;
        align-items: center;

        &.is-disabled {
          color: @light-gray;
          cursor: not-allowed;
        }

        &:not(.is-disabled):hover {
          background-color: @input-block-hover-color;
        }
      }

      svg {
        font-size: 14px;
      }

      > span:first-child {
        transform: rotate(180deg);
      }
    }
  }

  .dbm-textarea {
    position: relative;
    overflow: hidden;
    line-height: 20px;
    flex-direction: column;

    &.is-focused:not(.is-readonly) {
      border-color: @primary-color;
      outline: 0;
      box-shadow: 0 0 3px 0 @input-shadow-color;
    }

    &:hover:not(.is-disabled) {
      border-color: @gray-color;

      .is-show-clear-only-hover {
        display: flex;
      }
    }

    &.is-resizable {
      resize: vertical;

      > textarea {
        flex: 1;
      }
    }

    > textarea {
      width: 100%;
      padding: 5px 10px;
      line-height: 1.5;
      text-align: left;
      border: 0;
      border-radius: 2px;
      outline: none;
      resize: none;
    }

    .dbm-textarea-clear-icon {
      position: absolute;
      top: 5px;
      right: 10px;
      display: flex;
      font-size: 14px;
      color: @light-gray;
      cursor: pointer;

      &:hover {
        color: @gray-color;
      }

      &.is-show-clear-only-hover {
        display: none;
      }
    }

    .dbm-textarea-max-length {
      padding-right: 8px;
      margin: 0;
      margin-left: auto;
      font-size: 12px;
      text-align: right;
      transform: scale(0.8);
      justify-content: flex-end;

      &.is-over-limit {
        color: @danger-color;
      }

      span {
        color: @input-maxlength-color;
      }
    }
  }
</style>
