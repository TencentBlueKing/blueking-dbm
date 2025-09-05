<template>
  <div
    ref="root"
    class="bk-quick-search-value-tag-edit"
    :class="{
      'is-pop-menu-edit': isReadonly,
    }">
    <div style="position: absolute; z-index: -1; pointer-events: none; opacity: 0%">
      <!-- prettier-ignore -->
      <pre ref="calcTextWidth" style="display: block; padding: 0; margin: 0; font: inherit; visibility: hidden">{{ clacWidthText }}</pre>
    </div>
    <div :style="inputStyles">
      <div :style="placeholderStyles">{{ placeholderText }}</div>
      <textarea
        ref="editTextarea"
        v-model="latestEditValue"
        autocomplete="false"
        :name="config.name"
        :placeholder="isReadonly ? lastValueText : ''"
        spellcheck="false"
        :style="{
          'padding-bottom': isReadonly ? '' : `${valueTextSingleLineHeight}px`,
        }"
        @focus="handleFocus"
        @keydown="handleKeydown"
        @keyup="handleKeyup" />
      <div ref="valueMenuPopContent">
        <ValueMenu
          :config="config"
          :model-value="lastValue.values"
          @change="handleValueMenuChange" />
      </div>
    </div>
    <div
      v-if="isMultipleLintEdit || isSingleEdit"
      style="
        position: absolute;
        right: 0;
        bottom: 0;
        left: 0;
        padding-left: 4px;
        margin-left: -4px;
        color: #c4c6cc;
        pointer-events: none;
        background: #fafbfd;
      ">
      <span v-if="isMultipleLintEdit">支持输入多个值 ”Shift + Enter“ 换行，按”Enter“完成搜索</span>
      <span v-if="isSingleEdit">”Shift + Enter“ 换行，按”Enter“完成搜索</span>
    </div>
  </div>
</template>
<script lang="ts">
  let singleEndEditCallback: (() => void) | null = null;
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, onMounted, ref, useTemplateRef } from 'vue';

  import ValueMenu from '@components/db-quick-search/bk-quick-search/components/create-area/components/value-menu/Index.vue';
  import { comType } from '@components/db-quick-search/bk-quick-search/constants';
  import useMenuPop, { hideAll } from '@components/db-quick-search/bk-quick-search/hooks/useMenuPop';
  import useOutSideClick from '@components/db-quick-search/bk-quick-search/hooks/useOutSideClick';
  import type { IValue, Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { BK_QUICK_SEARCH } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { calcNeedShowValueMenu } from '@components/db-quick-search/bk-quick-search/utils';

  interface Props {
    config: ContextProps['data'][number];
    lastValue: IValue;
    lastValueText: string;
  }

  interface Emits {
    (e: 'change', value: IValue): void;
    (e: 'error', message: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const context = inject(BK_QUICK_SEARCH);

  const isReadonly = calcNeedShowValueMenu(props.config);
  const isMultipleLintEdit = props.config.type === comType.MULTIPLE_INPUT;
  const isSingleEdit = props.config.type === comType.INPUT;
  const valueTextSingleLineHeight = 22;

  const rootRef = useTemplateRef<HTMLElement>('root');
  const calcTextWidthRef = useTemplateRef<HTMLElement>('calcTextWidth');
  const editTextareaRef = useTemplateRef<HTMLTextAreaElement>('editTextarea');
  const popContentRef = useTemplateRef<HTMLElement>('valueMenuPopContent');

  const latestEditValue = ref(isReadonly ? '' : props.lastValue.values.map((item) => item.value).join('\n'));
  const inputStyles = ref({});

  const clacWidthText = computed(() =>
    props.lastValueText.length > latestEditValue.value.length ? props.lastValueText : latestEditValue.value,
  );
  const placeholderText = computed(() => {
    if (!isReadonly) {
      return `${latestEditValue.value}\u200B`;
    }
    return props.lastValueText.length > latestEditValue.value.length ? props.lastValueText : latestEditValue.value;
  });

  const placeholderStyles = computed<any>(() => {
    return {
      'max-height': isReadonly ? `${10 * valueTextSingleLineHeight}px` : 'unset',
      'min-height': `${valueTextSingleLineHeight}px`,
      overflow: 'hidden',
      'padding-bottom': isReadonly ? 0 : `${valueTextSingleLineHeight}px`,
      visibility: 'hidden',
      'white-space': 'pre-wrap',
      'word-break': 'break-all',
    };
  });

  const { show: showValueMenu } = useMenuPop(editTextareaRef, popContentRef);

  const endEditCallback = () => {
    emits('change', props.lastValue);
  };

  useOutSideClick(() => {
    endEditCallback();
  });

  // 计算输入框宽度，优先撑满
  const calcInputStyle = () => {
    setTimeout(() => {
      if (!calcTextWidthRef.value) {
        return;
      }
      inputStyles.value = {
        position: 'relative',
        width: isReadonly ? `${calcTextWidthRef.value.getBoundingClientRect().width}px` : '100%',
        'z-index': 1,
      };
    });
  };

  const handleKeydown = (event: KeyboardEvent) => {
    // 手动输入模式支持 Shfit + Enter 换行
    if (['Enter', 'NumpadEnter'].includes(event.code) && event.shiftKey && !isReadonly) {
      return true;
    }
    // 不响应方向键，Enter
    if (['ArrowDown', 'ArrowUp', 'Enter', 'NumpadEnter'].includes(event.code) && !event.isComposing) {
      event.preventDefault();
    }
    // 需要通过选择面板选择值，textarea 不响应任何输入
    if (isReadonly) {
      event.preventDefault();
    }
    calcInputStyle();
  };

  const handleKeyup = (event: KeyboardEvent) => {
    if (isReadonly) {
      return;
    }
    // 手动输入模式支持 Shfit + Enter 换行，默认换行行为
    if (['Enter', 'NumpadEnter'].includes(event.code) && event.shiftKey) {
      return true;
    }
    setTimeout(() => {
      // enter 提交
      if (['Enter', 'NumpadEnter'].includes(event.code) && !event.isComposing) {
        event.preventDefault();

        // 输入值校验
        let errorMessage = '';
        if ((isMultipleLintEdit || isSingleEdit) && _.isFunction(props.config.validator)) {
          let result: boolean | string = true;
          if (isMultipleLintEdit) {
            const valueList = context!.pasteParseMethod(latestEditValue.value);
            for (const valueItem of valueList) {
              const valueItemResult = props.config.validator!(valueItem);
              if (valueItemResult !== true) {
                result = valueItemResult;
                break;
              }
            }
          } else if (isSingleEdit) {
            result = props.config.validator(latestEditValue.value);
          }

          if (result && _.isString(result)) {
            errorMessage = result;
          } else {
            errorMessage = result ? '' : '格式不正确';
          }
          emits('error', errorMessage);
        }

        if (!errorMessage) {
          let values: IValue['values'] = [];

          if (latestEditValue.value) {
            values = [
              {
                label: latestEditValue.value,
                value: latestEditValue.value,
              },
            ];
            if (isMultipleLintEdit) {
              values = context!.pasteParseMethod(latestEditValue.value).map((item) => ({
                label: item,
                value: item,
              }));
            }
          }

          emits('change', {
            ...props.lastValue,
            values,
          });
        }
      }
    });
  };

  const handleValueMenuChange = (values: IValue['values']) => {
    emits('change', {
      ...props.lastValue,
      values,
    });
  };

  const handleFocus = () => {
    hideAll();
    if (isReadonly) {
      showValueMenu();
    }
  };

  // 退出编辑状态
  const handleOutsideClick = (event: Event) => {
    const eventPath = event.composedPath() as HTMLElement[];
    for (const target of eventPath) {
      // 如果点击的元素是已选择的 tag，则不开始选择
      // 已选择的 tag 的 role 属性为 search-value
      if (target === rootRef.value || /bk-quick-search-panel-theme/.test(target.dataset?.theme ?? '')) {
        return;
      }
    }
    endEditCallback();
  };

  onMounted(() => {
    calcInputStyle();
    if (singleEndEditCallback) {
      singleEndEditCallback();
    }
    singleEndEditCallback = endEditCallback;

    if (!isReadonly) {
      editTextareaRef.value!.selectionStart = 0;
      editTextareaRef.value!.selectionEnd = props.lastValueText.length;
    }
    // 切换编辑状态的的 click 事件这里也会监听到，加个延时，确保在非编辑状态下点击不会触发
    setTimeout(() => {
      editTextareaRef.value!.focus();
      document.addEventListener('click', handleOutsideClick);
    });
  });
  onBeforeUnmount(() => {
    document.removeEventListener('click', handleOutsideClick);
  });
</script>
<style lang="less">
  .bk-quick-search-value-tag-edit {
    position: relative;
    display: flex;
    width: auto;
    min-width: 30px;
    flex: 1;
    overflow: hidden;

    textarea {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      padding: 0;
      font-size: inherit;
      line-height: inherit;
      color: inherit;
      background: transparent;
      border: none;
      outline: none;
      resize: none;
    }
  }
</style>
