<template>
  <div class="create-validate-select-main">
    <BkSelect
      ref="selectRef"
      v-model="localValue"
      allow-create
      class="create-validate-select"
      :class="{ 'is-error': errorMessage }"
      :clearable="false"
      :disabled="disabled"
      error-display-type="tooltips"
      :filterable="false"
      :list="localList"
      :popover-options="{
        extCls: popoverOptionsExtCls,
      }"
      v-bind="$attrs"
      @change="handleChange">
      <template #trigger>
        <div
          class="create-validate-select-trigger"
          @click="handleTriggerClick">
          <BkInput
            v-model="inputValue"
            :maxlength="maxLength"
            :placeholder="placeholder"
            show-word-limit
            @blur="handleBlurInput"
            @enter="handleEnterInput"
            @input="handleInputValue" />
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
        <div class="create-validate-select-extension">
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
    <DbIcon
      v-if="errorMessage && errorMessage !== REQUIRED_MESSAGE"
      v-bk-tooltips="errorMessage"
      class="error-icon"
      type="exclamation-fill" />
  </div>
</template>
<script lang="ts" generic="T extends string | number">
  export interface Exposes<T> {
    clearValidate: () => void;
    getTotalList: () => SelectOption<T>[];
    tmpUpdateList: (list: SelectOption<T>[]) => void;
    validate: () => Promise<boolean>;
  }

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
  import BkSelect from 'bkui-vue/lib/select';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import useValidtor, { type Rules } from './useValidtor';

  type Emits = (e: 'change', value: T, isNew: boolean) => void;

  const props = withDefaults(defineProps<Props<T>>(), {
    disabled: false,
    maxLength: 50,
    options: () => [],
    placeholder: '',
    required: false,
    rules: () => [],
  });

  const emit = defineEmits<Emits>();

  const modelValue = defineModel<T>({
    default: '' as T,
  });

  const { t } = useI18n();
  const { message: errorMessage, validator } = useValidtor();

  const selectRef = ref<InstanceType<typeof BkSelect>>();
  const localValue = ref<T>('' as T);
  const inputValue = ref('');
  const localList = ref<SelectOption<T>[]>([]);
  const isExistdInList = ref(true);

  // 列表为空要把popover的边框去掉
  const popoverOptionsExtCls = computed(
    () => `create-validate-select-popover ${localList.value.length > 0 ? '' : ' create-validate-select-popover-empty'}`,
  );

  const mergeRules = computed(() => {
    if (props.required) {
      return [
        {
          message: REQUIRED_MESSAGE,
          trigger: 'blur',
          validator: (value: T) => !!value,
        },
        ...props.rules,
      ];
    }

    return props.rules;
  });

  const REQUIRED_MESSAGE = 'REQUIRED';
  const localNewList: SelectOption<T>[] = [];
  let localTotalList: SelectOption<T>[] = [];

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
      if (!inputValue.value) {
        inputValue.value = modelValue.value as string;
        setTimeout(() => {
          handleBlurInput();
        }, 500);
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => modelValue.value,
    (value) => {
      localValue.value = value;
      inputValue.value = localTotalList.find((item) => item.value === value)?.label ?? (modelValue.value as string);
    },
    {
      immediate: true,
    },
  );

  const handleValidate = (value: T) => {
    return validator(value, mergeRules.value);
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

  const handleAddNewOption = () => {
    handleEnterInput(inputValue.value as T);
  };

  const handleTriggerClick = (e: MouseEvent) => {
    if (selectRef.value?.isFocus) {
      e.stopPropagation();
    }
  };

  const handleBlurInput = async () => {
    const value = inputValue.value as T;
    const existOption = localList.value.find((item) => item.label === value);
    if (!value || existOption) {
      if (existOption) {
        modelValue.value = existOption.value as T;
        emit('change', existOption.value as T, false);
      }

      localList.value = _.cloneDeep(localTotalList);
      isExistdInList.value = true;
      return;
    }

    const isValid = await handleValidate(value);
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
    emit('change', value, true);
  };

  const handleEnterInput = async (value: T) => {
    const existOption = localList.value.find((item) => item.label === value);
    if (!value || existOption) {
      if (existOption) {
        modelValue.value = existOption.value as T;
        emit('change', existOption.value as T, false);
      }

      localList.value = _.cloneDeep(localTotalList);
      isExistdInList.value = true;
      return;
    }

    if (localList.value.length) {
      const defaultOption = localList.value[0];
      modelValue.value = defaultOption.value as T;
      isExistdInList.value = true;
      emit('change', defaultOption.value as T, false);
      return;
    }

    const isValid = await handleValidate(value);
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
    emit('change', value, true);
  };

  const handleInputValue = async (value: T) => {
    modelValue.value = value;
    if (!value) {
      localList.value = sortOptionList(_.cloneDeep(localTotalList));
      isExistdInList.value = true;
      return;
    }

    const isValid = await handleValidate(value);
    if (!isValid) {
      isExistdInList.value = true;
      return;
    }

    isExistdInList.value = localTotalList.some((item) => item.label === value);
    localList.value = filterAndSortOptionList(_.cloneDeep(localTotalList), String(value));
  };

  const handleChange = (value: T) => {
    handleValidate(value);
    modelValue.value = value;
    const option = localList.value.find((item) => item.value === value);
    inputValue.value = option?.label ?? '';
    const isNew = !!option?.isNew;
    emit('change', value, isNew);
  };

  defineExpose<Exposes<T>>({
    clearValidate() {
      errorMessage.value = '';
    },
    getTotalList() {
      return _.cloneDeep(localTotalList);
    },
    tmpUpdateList(list: SelectOption<T>[]) {
      localList.value = list;
    },
    validate() {
      return handleValidate(localValue.value);
    },
  });
</script>

<style lang="less">
  .create-validate-select-main {
    position: relative;
    width: 100%;

    .error-icon {
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      font-size: 14px;
      color: #ea3636;
    }

    .create-validate-select {
      &.is-error {
        .bk-input {
          border-color: #ea3636 !important;

          .bk-input--max-length {
            display: none;
          }
        }
      }

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
