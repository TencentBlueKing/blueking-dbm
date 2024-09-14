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
  <div class="table-edit-select">
    <div
      v-if="errorMessage"
      class="select-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <BkSelect
      v-model="localValue"
      auto-focus
      class="select-box"
      :class="{ 'is-error': Boolean(errorMessage) }"
      :clearable="false"
      :disabled="disabled"
      filterable
      :input-search="false"
      :placeholder="placeholder"
      @change="handleSelect"
      @clear="handleRemove">
      <SpecPanel
        v-for="(item, index) in list"
        :key="index"
        :data="item.specData">
        <template #hover>
          <BkOption
            :key="index"
            :label="item.label"
            :value="item.value">
            <div class="spec-display">
              <span class="text-overflow">
                {{ item.label }}
                <BkTag
                  v-if="item.isCurrentSpec"
                  size="small"
                  theme="info">
                  {{ t('当前规格') }}
                </BkTag>
              </span>
              <span class="count">
                {{ item.specData.count }}
              </span>
            </div>
          </BkOption>
        </template>
        <SpecPanel />
      </SpecPanel>
    </BkSelect>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import useValidtor, { type Rules } from '@components/render-table/hooks/useValidtor';

  import SpecPanel, { type SpecInfo } from './Panel.vue';

  type IKey = string | number;

  export interface IListItem {
    value: IKey;
    label: string;
    specData: SpecInfo;
    isCurrentSpec?: boolean;
  }

  interface Props {
    list: IListItem[];
    placeholder?: string;
    rules?: Rules;
    disabled?: boolean;
  }
  interface Emits {
    (e: 'change', value: IKey): void;
  }

  interface Exposes {
    getValue: () => Promise<IKey>;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '请输入',
    textarea: false,
    rules: () => [],
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IKey>({
    default: '',
  });

  const { t } = useI18n();
  const { message: errorMessage, validator } = useValidtor(props.rules);

  const localValue = ref<IKey>('');

  watch(
    modelValue,
    (value) => {
      localValue.value = value;
    },
    {
      immediate: true,
    },
  );

  // 选择
  const handleSelect = (value: IKey) => {
    localValue.value = value;
    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      modelValue.value = localValue.value;
      emits('change', localValue.value);
    });
  };

  // // 删除值
  const handleRemove = () => {
    localValue.value = '';
    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      modelValue.value = localValue.value;
      emits('change', localValue.value);
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .is-error {
    :deep(input) {
      background-color: #fff0f1;
      border-radius: 0;
    }

    :deep(.angle-up) {
      display: none !important;
    }
  }

  .table-edit-select {
    position: relative;
    display: flex;
    height: 42px;
    overflow: hidden;
    color: #63656e;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s;
    align-items: center;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

    :deep(.select-box) {
      width: 100%;
      height: 100%;
      padding: 0;
      background: transparent;
      border: none;
      outline: none;

      .bk-select-trigger {
        height: 100%;

        .bk-input {
          height: 100%;
          background: transparent;
          border: none;
        }
      }
    }

    .select-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 9999;
      display: flex;
      padding-right: 6px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }

  .spec-display {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: @gray-color;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }

  .bk-select-option {
    &.is-selected {
      .count {
        color: white;
        background-color: #a3c5fd;
      }
    }
  }
</style>
