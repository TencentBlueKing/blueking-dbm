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
    class="render-db-name">
    <div
      class="table-edit-tag"
      :class="{ ['is-error']: Boolean(errorMessage) }"
      @click="handleShowTips">
      <BkTagInput
        v-model="localValue"
        allow-auto-match
        allow-create
        clearable
        v-bind="$attrs"
        :disabled="disabled"
        has-delete-icon
        :max-data="single ? 1 : -1"
        :paste-fn="tagInputPasteFn"
        :placeholder="placeholder"
        @blur="handleBlur"
        @change="handleChange"
        @focus="handleFocus" />
      <div
        v-if="errorMessage"
        class="input-error">
        <DbIcon
          v-bk-tooltips="errorMessage"
          type="exclamation-fill" />
      </div>
    </div>
    <div style="display: none">
      <div
        ref="popRef"
        style="font-size: 12px; line-height: 24px; color: #63656e">
        <slot name="tip"> </slot>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';

  import { batchSplitRegex } from '@common/regex';

  import useValidtor, { type Rules } from '../../hooks/useValidtor';

  interface Props {
    placeholder?: string;
    modelValue?: string[];
    single?: boolean;
    rules?: Rules;
    disabled?: boolean;
  }

  interface Emits {
    (e: 'change', value: string[]): void;
    (e: 'update:modelValue', value: string[]): void;
    (e: 'focus'): void;
    (e: 'blur'): void;
  }

  interface Exposes {
    getValue: () => Promise<string[] | undefined>;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '',
    modelValue: undefined,
    single: false,
    rules: undefined,
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    default: any;
    tip: any;
  }>();

  const rootRef = ref();
  const popRef = ref();
  const localValue = ref(props.modelValue);
  const isFocus = ref(true);

  let tippyIns: Instance | undefined;

  const { message: errorMessage, validator } = useValidtor(props.rules);

  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localValue.value = props.modelValue;
      } else {
        localValue.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));

  const handleChange = (value: string[]) => {
    localValue.value = value;
    nextTick(() => {
      validator(localValue.value).then(() => {
        window.changeConfirm = true;
        emits('update:modelValue', value);
        emits('change', value);
      });
    });
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  const handleFocus = () => {
    isFocus.value = true;
    emits('focus');
  };

  const handleBlur = () => {
    emits('blur');
  };

  onMounted(() => {
    if (slots.tip) {
      tippyIns = tippy(rootRef.value as SingleTarget, {
        content: popRef.value,
        placement: 'top',
        appendTo: () => document.body,
        theme: 'light',
        maxWidth: 'none',
        trigger: 'manual',
        interactive: true,
        arrow: true,
        offset: [0, 18],
        zIndex: 9998,
        hideOnClick: true,
      });
    }
  });

  onBeforeUnmount(() => {
    if (slots.tip && tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  defineExpose<Exposes>({
    getValue: () =>
      validator(localValue.value).then(() => {
        emits('update:modelValue', localValue.value as string[]);
        emits('change', localValue.value as string[]);
        return localValue.value;
      }),
  });
</script>
<style lang="less">
  .table-edit-tag {
    position: relative;
    min-height: 42px;

    &.is-error {
      .bk-tag-input {
        .bk-tag-input-trigger {
          background: #fff0f1;

          .clear-icon {
            margin-right: 28px;
          }

          .placeholder {
            height: 42px;
            line-height: 42px;
          }
        }
      }
    }

    .bk-tag-input {
      .bk-tag-input-trigger {
        min-height: 42px;
        border-color: transparent;
        border-radius: 0;

        &:hover {
          background-color: #fafbfd;
          border-color: #a3c5fd !important;

          .clear-icon {
            display: block !important;
          }
        }

        &.active {
          border-color: #3a84ff !important;
        }

        .tag-input {
          background-color: transparent !important;
        }

        .tag-list {
          height: auto;
          max-height: 400px;
        }

        .clear-icon {
          display: none !important;
        }

        .placeholder {
          top: 0;
          height: 42px;
          padding-left: 8px;
          line-height: 42px;
        }
      }
    }

    .input-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 100;
      display: flex;
      padding-right: 10px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }
</style>
