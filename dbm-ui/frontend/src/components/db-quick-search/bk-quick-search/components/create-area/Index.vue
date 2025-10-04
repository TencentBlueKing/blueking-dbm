<template>
  <div
    ref="root"
    class="bk-quick-search-create-area"
    :class="{
      'is-focused': Boolean(currentDataConfig),
    }">
    <div
      v-if="localValue.name"
      class="create-area-name">
      {{ localValue.name }}:
    </div>
    <div
      v-if="data.length > 0"
      class="edit-area-input">
      <div :style="inputValueBoxStyles">{{ inputValue }}\u200B</div>
      <textarea
        ref="textarea"
        v-model="inputValue"
        name="search"
        :placeholder="currentPlaceholder"
        spellcheck="false"
        @blur="handleBlur"
        @focus="handleFocus"
        @keydown="handleKeydown"
        @keyup="handleKeyup" />
      <div
        v-if="isMultipleLintEdit || isSingleEdit"
        style="
          position: absolute;
          right: 0;
          bottom: 0;
          left: 0;
          padding-left: 4px;
          margin-left: -4px;
          overflow: hidden;
          color: #c4c6cc;
          text-overflow: ellipsis;
          white-space: nowrap;
          pointer-events: none;
          background: #fafbfd;
        ">
        <span v-if="isMultipleLintEdit">支持输入多个值 ”Shift + Enter“ 换行，按”Enter“完成搜索</span>
        <span v-if="isSingleEdit">”Shift + Enter“ 换行，按”Enter“完成搜索</span>
      </div>
    </div>
  </div>
  <div ref="keyMenu">
    <KeyMenu
      v-if="isShowKeyMenu"
      v-model="currentDataConfig"
      :data="data"
      @change="handleKeyMenuChange" />
  </div>
  <div ref="valueMenu">
    <ValueMenu
      v-if="isShowValueMenu"
      :key="currentDataConfig?.id || '--'"
      :config="currentDataConfig"
      @change="handleValueMenuChange" />
  </div>
  <div ref="suggestMenu">
    <SuggestMenu
      v-if="isShowSuggestMenu"
      :data="data"
      :keyword="inputValue"
      @change="handleSuggestMenuChange" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { onMounted, ref, shallowRef, useTemplateRef } from 'vue';

  import useMenuPop, { update as updateMenuPop } from '@components/db-quick-search/bk-quick-search/hooks/useMenuPop';
  import useOutSideClick from '@components/db-quick-search/bk-quick-search/hooks/useOutSideClick';
  import type { IValue, Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { BK_QUICK_SEARCH } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { calcNeedShowValueMenu } from '@components/db-quick-search/bk-quick-search/utils';

  import { comType } from '../../constants';

  import KeyMenu from './components/KeyMenu.vue';
  import SuggestMenu from './components/SuggestMenu.vue';
  import ValueMenu from './components/value-menu/Index.vue';

  interface Props {
    data: ContextProps['data'];
    defaultStartSelect?: boolean;
    placeholder: string;
  }

  interface Emits {
    (e: 'change', value: IValue): void;
    (e: 'focus'): void;
    (e: 'blur'): void;
    (e: 'remove'): void;
    (e: 'error', message: string): void;
  }

  interface Expose {
    restartSelect: () => void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const genDefaultValue = (): IValue => ({
    id: '',
    name: '',
    values: [],
  });

  const context = inject(BK_QUICK_SEARCH);

  const rootRef = useTemplateRef<HTMLElement>('root');
  const keyMenuRef = useTemplateRef<HTMLElement>('keyMenu');
  const valueMenuRef = useTemplateRef<HTMLElement>('valueMenu');
  const suggestMenuRef = useTemplateRef<HTMLElement>('suggestMenu');
  const textareaRef = useTemplateRef<HTMLTextAreaElement>('textarea');

  const inputValue = ref('');
  const currentDataConfig = shallowRef<ContextProps['data'][number]>();
  const localValue = ref(genDefaultValue());

  const currentPlaceholder = computed(() => {
    if (!currentDataConfig.value) {
      return props.placeholder;
    }
    if (currentDataConfig.value.placeholder) {
      return currentDataConfig.value.placeholder;
    }
    if (currentDataConfig.value.list || _.isFunction(currentDataConfig.value.remoteMethod)) {
      return '请选择';
    }
    return '请输入';
  });
  const isNeedShowValueMenu = computed(() => {
    if (!currentDataConfig.value || props.data.length < 1) {
      return false;
    }
    return calcNeedShowValueMenu(currentDataConfig.value);
  });
  const isMultipleLintEdit = computed(() => currentDataConfig.value?.type === comType.MULTIPLE_INPUT);
  const isSingleEdit = computed(() => currentDataConfig.value?.type === comType.INPUT);
  const inputValueBoxStyles = computed<any>(() => {
    const baseStyles = {
      'min-height': '22px',
      visibility: 'hidden',
      'white-space': 'pre-wrap',
      'word-break': 'break-all',
    };
    if (currentDataConfig.value) {
      Object.assign(baseStyles, {
        'padding-bottom': isNeedShowValueMenu.value ? 0 : `22px`,
      });
    }

    return baseStyles;
  });

  const { hide: hideKeyMenu, isShow: isShowKeyMenu, show: showKeyMenu } = useMenuPop(textareaRef, keyMenuRef);

  const { hide: hideValueMenu, isShow: isShowValueMenu, show: showValueMenu } = useMenuPop(textareaRef, valueMenuRef);

  const {
    hide: hideSuggestMenu,
    isShow: isShowSuggestMenu,
    show: showSuggestMenu,
  } = useMenuPop(rootRef, suggestMenuRef);

  const hideMenuPop = () => {
    hideKeyMenu();
    hideValueMenu();
    hideSuggestMenu();
  };

  const restartSelect = () => {
    hideMenuPop();
    localValue.value = genDefaultValue();
    inputValue.value = '';
    setTimeout(() => {
      if (props.data.length > 0) {
        showKeyMenu();
      }
      currentDataConfig.value = undefined;
    }, 100);
  };

  const showCurrentPop = () => {
    hideMenuPop();
    if (props.data.length < 1) {
      return;
    }
    // 选中了 Key
    if (currentDataConfig.value) {
      if (isNeedShowValueMenu.value) {
        // value 需要通过下拉面板设置
        showValueMenu();
      }
      return;
    }
    // 没有选中 key 但是输入框不为空，显示 suggest menu
    if (inputValue.value) {
      showSuggestMenu();
      return;
    }
    // 默认显示 key menu
    showKeyMenu();
  };

  useOutSideClick(() => {
    hideMenuPop();
  });

  // 获得焦点自动弹框 key 选择面板
  const handleFocus = () => {
    emits('focus');
    // 聚焦时会整个输入框有高度变化，需要延迟显示面板
    setTimeout(() => {
      showCurrentPop();
    }, 20);
  };

  // 失去焦点
  const handleBlur = () => {
    emits('blur');
  };

  // 选择 key 完成，textarea 自动获得焦点
  const handleKeyMenuChange = (keyData: ContextProps['data'][number]) => {
    localValue.value.id = keyData.id;
    localValue.value.name = keyData.name;
    localValue.value.values = [];
    textareaRef.value!.focus();
    showCurrentPop();
  };

  // 选择 value 后提交操作结果，生成 tag
  const handleValueMenuChange = (valueData: IValue['values']) => {
    // value 值不能为空
    if (valueData.length > 0) {
      localValue.value.values = valueData;
      emits('change', _.cloneDeep(localValue.value));
    }
    restartSelect();
  };

  const handleSuggestMenuChange = (value: IValue) => {
    emits('change', _.cloneDeep(value));
    restartSelect();
  };

  const handleKeydown = (event: KeyboardEvent) => {
    // 手动输入模式支持 Shfit + Enter 换行
    if (
      ['Enter', 'NumpadEnter'].includes(event.code) &&
      event.shiftKey &&
      currentDataConfig.value &&
      !isNeedShowValueMenu.value
    ) {
      return true;
    }
    if (['ArrowDown', 'ArrowUp', 'Enter', 'NumpadEnter'].includes(event.code) && !event.isComposing) {
      event.preventDefault();
    }
    // 通过选择面板选择值时只识别删除操作
    if (isNeedShowValueMenu.value && !['Backspace'].includes(event.code)) {
      event.preventDefault();
      return false;
    }
  };

  let latestInputValue = '';
  const handleKeyup = (event: KeyboardEvent) => {
    setTimeout(() => {
      // 在选择面板中选择值，不想要输入框输入
      if (isNeedShowValueMenu.value) {
        // 重置任何输入
        inputValue.value = '';
      }
      // 手动输入模式支持 Shfit + Enter 换行，默认换行行为
      if (['Enter', 'NumpadEnter'].includes(event.code) && event.shiftKey) {
        return true;
      }

      if (['ArrowDown', 'ArrowUp'].includes(event.code)) {
        event.preventDefault();
      } else if (['Enter', 'NumpadEnter'].includes(event.code) && !event.isComposing) {
        event.preventDefault();
        // 没有选择 key
        if (isShowKeyMenu.value || isShowSuggestMenu.value || !currentDataConfig.value) {
          return;
        }
        // 没有输入任何值
        if (!inputValue.value) {
          return;
        }

        if (isNeedShowValueMenu.value) {
          return;
        }

        // value 使用 input 的值
        let errorMessage = '';
        if ((isMultipleLintEdit || isSingleEdit) && _.isFunction(currentDataConfig.value.validator)) {
          let result: boolean | string = true;
          if (isMultipleLintEdit) {
            const valueList = context!.pasteParseMethod(inputValue.value);
            for (const valueItem of valueList) {
              const valueItemResult = currentDataConfig.value!.validator!(valueItem);
              if (valueItemResult !== true) {
                result = valueItemResult;
                break;
              }
            }
          } else if (isSingleEdit) {
            result = currentDataConfig.value.validator(inputValue.value);
          }

          if (result && _.isString(result)) {
            errorMessage = result;
          } else {
            errorMessage = result ? '' : '格式不正确';
          }
          emits('error', errorMessage);
        }
        if (!errorMessage) {
          // 默认直接使用输入的值搜索
          let values = [
            {
              label: inputValue.value,
              value: inputValue.value,
            },
          ];

          // 如果允许输入多个需要解析分隔符
          if (currentDataConfig.value.type === comType.MULTIPLE_INPUT) {
            values = context!.pasteParseMethod(inputValue.value).map((item) => ({
              label: item,
              value: item,
            }));
          }

          handleValueMenuChange(values);
        }
        return;
      } else if (['Backspace'].includes(event.code)) {
        if (currentDataConfig.value) {
          if (inputValue.value || latestInputValue) {
            // 编辑输入框更新当前弹出面板位置
            showCurrentPop();
          } else if (!inputValue.value && !latestInputValue) {
            // 删除最后一个选中的 tag
            restartSelect();
          }
        } else {
          if (!inputValue.value && !latestInputValue) {
            // 已经清空输入框，继续删除则是删除已选 key
            emits('remove');
            restartSelect();
          } else if (!inputValue.value && latestInputValue) {
            // 删除输入框最后一个字符，弹出 key 面板重新选择
            restartSelect();
          } else if (inputValue.value && latestInputValue) {
            // 编辑输入框更新当前弹出面板位置
            updateMenuPop();
          }
        }
      } else if (!currentDataConfig.value) {
        if (inputValue.value) {
          showSuggestMenu();
        }
      } else if (currentDataConfig.value) {
        if (isNeedShowValueMenu.value) {
          showValueMenu();
        }
      }
      latestInputValue = inputValue.value;
    });
  };

  onMounted(() => {
    setTimeout(() => {
      if (props.defaultStartSelect) {
        textareaRef.value!.focus();
      }
    });
  });

  defineExpose<Expose>({
    restartSelect,
  });
</script>
<style lang="less">
  .bk-quick-search-create-area {
    position: relative;
    display: inline-flex;
    max-width: 100%;
    min-width: 80px;
    min-height: 22px;
    margin-top: 4px;
    line-height: 22px;
    color: #63656e;
    flex: 1 0 auto;
    align-items: self-start;

    &.is-focused {
      flex: 0 0 100%;
    }

    .create-area-name {
      flex: 0 0 auto;
      padding-right: 4px;
      word-break: keep-all;
    }

    .edit-area-input {
      position: relative;
      min-height: 100%;
      flex: 1;
      overflow: hidden;

      textarea {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        padding: 0;
        overflow: hidden;
        font-size: inherit;
        line-height: inherit;
        color: inherit;
        white-space: pre-wrap;
        background: transparent;
        border: none;
        outline: none;
        resize: none;

        &::placeholder {
          color: #c4c6cc;
        }
      }
    }
  }

  .bk-quick-search-panel-footer {
    display: flex;
    height: 40px;
    padding: 8px 12px;
    border-top: 1px solid #dcdee5;
    user-select: none;
    justify-content: flex-end;
    align-items: center;
  }

  .bk-quick-search-panel-submit-tips {
    display: flex;
    margin-right: auto;
    font-size: 12px;
    color: #7a8599;

    .action-tips {
      margin-right: 12px;
    }

    .tag {
      display: inline-flex;
      height: 16px;
      padding: 0 2px;
      margin-right: 4px;
      font-size: 11px;
      font-weight: 600;
      color: #a3b1cc;
      background: rgb(163 177 204 / 16.1%);
      border: 1px solid rgb(163 177 204 / 30.2%);
      border-radius: 2px;
      align-items: center;
      justify-content: center;
    }
  }
</style>
