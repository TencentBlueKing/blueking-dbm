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
            :value="item.value" />
        </template>
        <SpecPanel />
      </SpecPanel>
    </BkSelect>
  </div>
</template>
<script lang="ts">
  type IKey = string | number;

  export interface IListItem {
    value: IKey;
    label: string;
    specData: SpecInfo;
  }
</script>
<script setup lang="ts">
  import useValidtor, { type Rules } from '@views/redis/common/edit/hooks/useValidtor';

  import type { SpecInfo } from './SpecPanel.vue';
  import SpecPanel from './SpecPanel.vue';

  interface Props {
    list: Array<IListItem>;
    modelValue?: IKey;
    placeholder?: string;
    rules?: Rules;
    disabled?: boolean;
  }
  interface Emits {
    (e: 'update:modelValue', value: IKey): void;
    (e: 'change', value: IKey): void;
  }

  interface Exposes {
    getValue: () => Promise<IKey>;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
    placeholder: '请输入',
    textarea: false,
    rules: () => [],
    disabled: false,
  });
  const emits = defineEmits<Emits>();

  const { message: errorMessage, validator } = useValidtor(props.rules);

  const localValue = ref<IKey>('');

  watch(
    () => props.modelValue,
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
      emits('update:modelValue', localValue.value);
      emits('change', localValue.value);
    });
  };

  // // 删除值
  const handleRemove = () => {
    localValue.value = '';
    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      emits('update:modelValue', localValue.value);
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
</style>
