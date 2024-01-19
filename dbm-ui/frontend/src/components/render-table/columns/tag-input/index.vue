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
    class="render-db-name"
    :class="{'render-db-name-scroll': isFocus}">
    <span @click="handleShowTips">
      <div
        class="table-edit-tag"
        :class="{['is-error']: Boolean(errorMessage),}">
        <BkTagInput
          v-model="localValue"
          allow-auto-match
          allow-create
          :clearable="false"
          collapse-tags
          has-delete-icon
          :max-data="single ? 1 : -1"
          :placeholder="placeholder"
          @blur="handleBlur"
          @change="handleChange"
          @focus="handleFocus"
          @keydown="handleKeyDown" />
        <div
          v-if="errorMessage"
          class="input-error">
          <DbIcon
            v-bk-tooltips="errorMessage"
            type="exclamation-fill" />
        </div>
      </div>
    </span>
    <div style="display: none;">
      <div
        ref="popRef"
        style=" font-size: 12px; line-height: 24px;color: #63656e;">
        <slot name="tip">
          <p>{{ t('%：匹配任意长度字符串，如 a%， 不允许独立使用') }}</p>
          <p>{{ t('？： 匹配任意单一字符，如 a%?%d') }}</p>
          <p>{{ t('* ：专门指代 ALL 语义, 只能独立使用') }}</p>
          <p>{{ t('注：含通配符的单元格仅支持输入单个对象') }}</p>
          <p>{{ t('Enter 完成内容输入') }}</p>
        </slot>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';

  import { t } from '@locales/index';

  import useValidtor, {
    type Rules,
  } from '../../hooks/useValidtor';

  interface Props {
    placeholder?: string,
    modelValue?: string [],
    single?: boolean,
    rules?: Rules
  }

  interface Emits {
    (e: 'change', value: string []): void,
    (e: 'update:modelValue', value: string []): void
  }

  interface Exposes {
    getValue: () => Promise<string[] | undefined>
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '',
    modelValue: undefined,
    single: false,
    rules: undefined,
  });

  const emits = defineEmits<Emits>();

  const rootRef = ref();
  const popRef = ref();
  const localValue = ref(props.modelValue);
  const isFocus = ref(false);

  let tippyIns: Instance | undefined;
  let clipBoardData = '';

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);


  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localValue.value = props.modelValue;
    } else {
      localValue.value = [];
    }
  }, {
    immediate: true,
  });

  const handleChange = (value: string[]) => {
    localValue.value = value;
    nextTick(() => {
      validator(localValue.value)
        .then(() => {
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
  };

  const handleBlur = () => {
    isFocus.value = false;
  };

  const handleClipboardPaste = (e: ClipboardEvent) => {
    const clipboard = e.clipboardData || window.clipboardData;
    clipBoardData = clipboard.getData('text/plain');
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.ctrlKey && e.key === 'v') {
      setTimeout(() => {
        if (clipBoardData === '') {
          return;
        }
        localValue.value = clipBoardData.split('\n');
      });
    }
  };

  onMounted(() => {
    window.addEventListener('paste', handleClipboardPaste);
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
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
    window.removeEventListener('paste', handleClipboardPaste);
  });

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value)
        .then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
.render-db-name {
  display: block;

  :deep(.bk-tag-input-trigger) {
    .tag-list {
      height: 40px;
    }
  }

}

.render-db-name-scroll {
  position: relative;
  padding: 0;
  margin: 0;

  :deep(.bk-tag-input) {
    position: absolute;
    top: -21px;
    z-index: 99;
    width: 100%;

    .bk-tag-input-trigger {
      .tag-list {
        height: auto;
        max-height: 135px;
      }
    }

  }
}
</style>
<style lang="less">
.table-edit-tag {
  position: relative;

  &.is-error {
    .bk-tag-input {
      .bk-tag-input-trigger {
        background: #fff0f1;

        .placeholder {
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
      }

      &.active {
        border-color: #3a84ff !important;
      }

      .tag-input {
        background-color: transparent !important;
      }

      .placeholder {
        top: 0;
        height: 42px;
        line-height: 42px;
      }
    }
  }

  .input-error {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    display: flex;
    padding-right: 10px;
    font-size: 14px;
    color: #ea3636;
    align-items: center;
  }
}
</style>
