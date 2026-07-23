<template>
  <div class="create-validate-select-main">
    <BkForm
      ref="formRef"
      class="create-validate-select-form"
      :model="formData"
      :rules="formRules"
      @validate="handleFormValidate">
      <BkFormItem
        class="create-validate-select-form-item"
        :class="{ 'is-hide-error-tip': isHideErrorTip }"
        error-display-type="tooltips"
        label=""
        label-width="0"
        property="value"
        :required="required">
        <BkSelect
          ref="selectRef"
          v-model="formData.value"
          allow-create
          class="create-validate-select"
          :clearable="false"
          :disabled="disabled"
          :filterable="false"
          :list="localList"
          :popover-options="{
            extCls: popoverOptionsExtCls,
          }"
          v-bind="$attrs"
          @change="(value) => handleChange(value)"
          @toggle="handleTogglePopover">
          <template #trigger>
            <div
              class="create-validate-select-trigger"
              @click="handleTriggerClick">
              <BkInput
                ref="inputRef"
                v-model="inputValue"
                :maxlength="maxLength"
                :placeholder="placeholder"
                show-word-limit
                @blur="handleBlurInput"
                @enter="handleEnterInput"
                @focus="handleFocusInput"
                @input="handleInputValue"
                @keydown="handleKeyDown" />
            </div>
          </template>
          <template #optionRender="{ item }">
            <div class="create-validate-select-option-main">
              <div
                v-overflow-tips
                class="option-label">
                {{ item.label }}
              </div>
              <BkTag
                v-if="item.isNew"
                size="small"
                theme="success">
                NEW
              </BkTag>
            </div>
          </template>
          <template #extension>
            <div
              class="create-validate-select-extension"
              :class="{ 'is-only-create-option': !localList.length && !isExistdInList }">
              <div
                v-if="!isExistdInList"
                class="add-new-option-main"
                @click.stop="handleAddNewOption">
                <DbIcon
                  class="add-option-icon"
                  type="add" />
                <span class="ml-5 mr-12">{{ t('新建') }}</span>
                <div
                  v-overflow-tips
                  class="new-option-name">
                  {{ inputValue }}
                </div>
              </div>
              <div
                v-if="$slots.extension"
                class="extension-content">
                <slot name="extension" />
              </div>
            </div>
          </template>
        </BkSelect>
      </BkFormItem>
    </BkForm>
  </div>
</template>
<script lang="ts" generic="T extends string | number">
  export interface Exposes<T> {
    clearValidate: () => void;
    getTotalList: () => SelectOption<T>[];
    tmpUpdateList: (list: SelectOption<T>[]) => void;
    validate: () => Promise<boolean>;
  }

  export type Rules = Array<{
    message: string | (() => string);
    trigger?: string;
    validator: (value: any) => boolean | string | Promise<boolean | string>;
  }>;

  export interface Props<T> {
    disabled?: boolean;
    maxLength?: number;
    options?: SelectOption<T>[];
    placeholder?: string;
    required?: boolean;
    rules?: Rules;
  }

  interface SelectOption<T> {
    isNew?: boolean;
    label: string;
    value: T;
  }
</script>

<script setup lang="ts" generic="T extends string | number">
  import BkForm from 'bkui-vue/lib/form';
  import BkSelect from 'bkui-vue/lib/select';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  type Emits = (e: 'change', value: T, isNew: boolean) => void;

  const props = withDefaults(defineProps<Props<T>>(), {
    disabled: false,
    maxLength: 50,
    options: () => [],
    placeholder: '',
    required: false,
    rules: () => [],
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<T>({
    default: '' as T,
  });

  const { t } = useI18n();

  const formRef = ref<InstanceType<typeof BkForm>>();
  const selectRef = ref<InstanceType<typeof BkSelect>>();
  const inputRef = ref<InstanceType<typeof BkInput>>();
  const inputValue = ref('');
  const localList = ref<SelectOption<T>[]>([]);
  const isExistdInList = ref(true);
  const isHideErrorTip = ref(false);

  const formData = reactive({
    value: '' as T,
  });

  // 列表为空要把popover的边框去掉
  const popoverOptionsExtCls = computed(
    () => `create-validate-select-popover ${localList.value.length > 0 ? '' : ' create-validate-select-popover-empty'}`,
  );

  const formRules = computed(() => ({
    value: props.rules,
  }));

  const localNewList: SelectOption<T>[] = [];

  let localTotalList: SelectOption<T>[] = [];
  let isInputOrSelectValueChanged = false;
  let currentIndex = -1;

  watch(
    () => props.options,
    (options) => {
      localList.value = options;
      localTotalList = _.cloneDeep(options);
      if (!options.length) {
        return;
      }

      inputValue.value = options.find((item) => item.value === modelValue.value)?.label ?? '';
      // 不存在就新建一个选项
      if (!inputValue.value && modelValue.value) {
        inputValue.value = modelValue.value as string;
        setTimeout(() => {
          handleBlurInput();
        }, 500);
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    () => modelValue.value,
    (value) => {
      (formData as { value: T }).value = value;
      inputValue.value = localTotalList.find((item) => item.value === value)?.label ?? (modelValue.value as string);
    },
    {
      immediate: true,
    },
  );

  const handleFormValidate = (_property: string, result: boolean) => {
    isHideErrorTip.value = !result && formData.value === '';
  };

  const handleValidate = async () => {
    try {
      await formRef.value?.validate('value');
      return true;
    } catch {
      return false;
    }
  };

  /**
   * 自然排序选项
   */
  const naturalSort = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true });

  /**
   * 排序选项列表
   */
  const sortOptionList = (list: SelectOption<T>[]) => [...list].sort((a, b) => naturalSort(a.label, b.label));

  /**
   * 过滤并排序选项
   */
  const filterAndSortOptionList = (list: SelectOption<T>[], keyword: string) => {
    const searchText = String(keyword);
    const prefixList: SelectOption<T>[] = [];
    const containsList: SelectOption<T>[] = [];

    list.forEach((item) => {
      if (!item.label.includes(searchText)) {
        return;
      }
      if (item.label.startsWith(searchText)) {
        prefixList.push(item);
      } else {
        containsList.push(item);
      }
    });

    return [...sortOptionList(prefixList), ...sortOptionList(containsList)];
  };

  /**
   * 悬浮第一个选项
   */
  const handleHoverFirstOption = () => {
    hoverOptionByIndex(0);
  };

  /**
   * 将指定索引的选项滚动到可视区域
   */
  const scrollOptionIntoView = (index: number) => {
    nextTick(() => {
      const contentEl = selectRef.value?.contentRef;
      if (!contentEl) {
        return;
      }

      const optionEls = contentEl.querySelectorAll('.bk-select-option');
      const targetOption = optionEls[index] as HTMLElement | undefined;
      targetOption?.scrollIntoView({ block: 'nearest' });
    });
  };

  /**
   * 悬浮指定索引的选项
   */
  const hoverOptionByIndex = (index: number) => {
    const contentEl = selectRef.value?.contentRef;
    if (!contentEl) {
      return;
    }

    const optionEls = contentEl.querySelectorAll('.bk-select-option');
    const targetOption = optionEls[index] as HTMLElement | undefined;
    targetOption?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  };

  /**
   * 清除所有选项的悬浮态
   */
  const clearAllOptionHover = () => {
    const contentEl = selectRef.value?.contentRef;
    if (!contentEl) {
      return;
    }

    const optionEls = contentEl.querySelectorAll('.bk-select-option');
    optionEls.forEach((option) => {
      option.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
    });
  };

  const handleHidePopoverAndBlurInput = () => {
    selectRef.value?.hidePopover();
    inputRef.value?.blur();
  };

  const handleAddNewOption = () => {
    handleEnterInput(inputValue.value as T);
    nextTick(() => {
      handleHidePopoverAndBlurInput();
    });
  };

  const handleTriggerClick = (e: MouseEvent) => {
    if (selectRef.value?.isFocus || selectRef.value?.isPopoverShow) {
      e.stopPropagation();
      return;
    }
  };

  const handleFocusInput = () => {
    setTimeout(() => {
      if (selectRef.value?.isFocus && selectRef.value?.isPopoverShow) {
        return;
      }
      selectRef.value?.showPopover();
    }, 100);
  };

  const handleBlurInput = () => {
    setTimeout(async () => {
      // selectRef.value!.hidePopover();
      // selectRef.value!.isFocus = false;
      if (isInputOrSelectValueChanged) {
        isInputOrSelectValueChanged = false;
        return;
      }

      // 输入框保持原样，高亮丢失
      const currentOptionIndex = localList.value.findIndex((item) => item.label === modelValue.value);
      if (currentIndex !== currentOptionIndex) {
        currentIndex = currentOptionIndex;
        return;
      }

      if (inputValue.value === modelValue.value) {
        isExistdInList.value = true;
        return;
      }

      const value = inputValue.value as T;
      const existOption = localList.value.find((item) => item.label === value);
      if (!value || existOption) {
        if (existOption) {
          modelValue.value = existOption.value as T;
          emits('change', existOption.value as T, false);
        }

        localList.value = _.cloneDeep(localTotalList);
        isExistdInList.value = true;
        return;
      }

      const isValid = await handleValidate();
      if (!isValid) {
        return;
      }

      localNewList.unshift({
        isNew: true,
        label: String(value),
        value: value as any,
      });
      localTotalList = [...props.options, ...localNewList];

      localList.value = _.cloneDeep(localTotalList);
      isExistdInList.value = true;
      modelValue.value = value;
      emits('change', value, true);
    });
  };

  const handleEnterInput = async (value: T) => {
    if (isInputOrSelectValueChanged) {
      isInputOrSelectValueChanged = false;
      return;
    }

    const currentOptionIndex = localList.value.findIndex((item) => item.label === value);
    if (currentOptionIndex !== -1 && currentIndex !== currentOptionIndex) {
      const option = localList.value[currentIndex];
      modelValue.value = option.value as T;
      nextTick(() => {
        emits('change', option.value as T, false);
        handleHidePopoverAndBlurInput();
      });
      return;
    }

    const existOption = localList.value[currentOptionIndex];
    if (!value || existOption) {
      if (existOption) {
        modelValue.value = existOption.value as T;
        emits('change', existOption.value as T, false);
      }

      localList.value = _.cloneDeep(localTotalList);
      isExistdInList.value = true;
      handleHidePopoverAndBlurInput();
      return;
    }

    // 仅 1 条已有候选 → 选中该项；
    if (localList.value.length && localList.value.length === 1) {
      const defaultOption = localList.value[0];
      modelValue.value = defaultOption.value as T;
      isExistdInList.value = true;
      emits('change', defaultOption.value as T, false);
      handleHidePopoverAndBlurInput();
      return;
    }

    const isValid = await handleValidate();
    if (!isValid) {
      return;
    }

    localNewList.unshift({
      isNew: true,
      label: String(value),
      value: value as any,
    });
    localTotalList = [...props.options, ...localNewList];
    localList.value = _.cloneDeep(localTotalList);
    isExistdInList.value = true;
    modelValue.value = value;
    emits('change', value, true);
    handleHidePopoverAndBlurInput();
  };

  const handleInputValue = (value: T) => {
    // isInputOrSelectValueChanged = true;
    modelValue.value = value;
    nextTick(async () => {
      if (!value) {
        localList.value = sortOptionList(_.cloneDeep(localTotalList));
        isExistdInList.value = true;
        currentIndex = -1;
        return;
      }

      const isValid = await handleValidate();
      if (!isValid) {
        isExistdInList.value = true;
        localList.value = [];
        currentIndex = -1;
        return;
      }

      isExistdInList.value = localTotalList.find((item) => item.label === value);
      localList.value = filterAndSortOptionList(_.cloneDeep(localTotalList), String(value));
      currentIndex = localList.value.findIndex((item) => item.label === value);
      if (localList.value.length === 1) {
        nextTick(() => {
          handleHoverFirstOption();
        });
      } else {
        nextTick(() => {
          clearAllOptionHover();
        });
      }
    });
  };

  const handleChange = (value: T, isAutoChanged = true) => {
    isExistdInList.value = true;
    isInputOrSelectValueChanged = isAutoChanged;
    if (isAutoChanged) {
      handleValidate();
    }
    modelValue.value = value;
    const option = localList.value.find((item) => item.value === value);
    inputValue.value = option?.label ?? '';
    const isNew = !!option?.isNew;
    emits('change', value, isNew);
    nextTick(() => {
      isInputOrSelectValueChanged = false;
    });
  };

  const handleKeyDown = (_value: string, e: KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
    }

    setTimeout(() => {
      if (currentIndex === -1) {
        currentIndex = localList.value.findIndex((item) => item.label === modelValue.value);
      }
      if (e.key === 'ArrowDown') {
        if (currentIndex < localList.value.length - 1) {
          currentIndex = currentIndex + 1;
          hoverOptionByIndex(currentIndex);
          scrollOptionIntoView(currentIndex);
        }
        return;
      }

      if (e.key === 'ArrowUp') {
        if (currentIndex === -1) {
          return;
        }

        currentIndex = currentIndex - 1;
        hoverOptionByIndex(currentIndex);
        scrollOptionIntoView(currentIndex);
        return;
      }

      if (e.key === 'Tab') {
        selectRef.value?.hidePopover();
      }
    });
  };

  const handleTogglePopover = (isShow: boolean) => {
    if (isShow) {
      if (localList.value.length === 1) {
        currentIndex = 0;
      } else {
        currentIndex = -1;
        setTimeout(() => {
          clearAllOptionHover();
        }, 100);
      }
    }
  };

  defineExpose<Exposes<T>>({
    clearValidate() {
      formRef.value?.clearValidate();
    },
    getTotalList() {
      return _.cloneDeep(localTotalList);
    },
    tmpUpdateList(list: SelectOption<T>[]) {
      localList.value = list;
    },
    validate: handleValidate,
  });
</script>

<style lang="less">
  .create-validate-select-main {
    position: relative;
    width: 100%;

    .create-validate-select-form {
      width: 100%;

      .create-validate-select-form-item {
        margin-bottom: 0;

        &.is-error {
          .create-validate-select {
            .bk-input {
              border-color: #ea3636 !important;

              .bk-input--max-length {
                display: none;
              }
            }
          }
        }

        &.is-hide-error-tip {
          .bk-form-error-tips {
            display: none !important;
          }
        }
      }
    }

    .create-validate-select {
      .bk-select-trigger {
        .angle-down {
          display: none !important;
        }
      }
    }
  }

  .create-validate-select-popover {
    .bk-select-empty {
      display: none !important;
    }

    .bk-select-content {
      .create-validate-select-option-main {
        display: flex;
        width: 100%;
        align-items: center;

        .option-label {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .bk-select-extension {
      height: auto !important;
      border: none !important;

      .create-validate-select-extension {
        display: flex;
        width: 100%;
        flex-direction: column;

        &.is-only-create-option {
          border: 1px solid #dcdee5;
          border-radius: 2px;
          box-shadow: 0 2px 6px 0 rgb(0 0 0 / 10%);
        }

        .add-new-option-main {
          display: flex;
          height: 32px;
          padding: 6px 12px;
          color: #3a84ff;
          cursor: pointer;
          border-top: 1px solid #f0f1f5;
          align-items: center;

          &:hover {
            background-color: #e1ecff;
          }

          .add-option-icon {
            font-weight: 400;
          }

          .new-option-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;

            &::before {
              content: '"';
            }

            &::after {
              content: '"';
            }
          }
        }

        .extension-content {
          display: flex;
          align-items: center;
          height: 40px;
          background-color: #fafbfd;
          border-top: 1px solid #dcdee5;
          border-radius: 0 0 2px 2px;
        }
      }
    }
  }

  .create-validate-select-popover-empty {
    border: none !important;
    box-shadow: none !important;
  }
</style>
