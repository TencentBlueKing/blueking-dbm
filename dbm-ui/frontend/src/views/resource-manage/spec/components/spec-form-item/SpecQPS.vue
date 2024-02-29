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
  <BkFormItem
    :label="$t('单机QPS')"
    property="qps"
    required
    :rules="qpsRules">
    <span
      v-bk-tooltips="{
        content: $t('不支持修改'),
        disabled: !isEdit,
      }"
      class="inline-block">
      <BkInput
        v-model="modelValue.min"
        :disabled="isEdit"
        :max="10000000"
        :min="1"
        style="width: 140px"
        type="number"
        @change="handleLimitChange('min')" />
    </span>
    <span class="item-desc">{{ $t('至') }}</span>
    <span
      v-bk-tooltips="{
        content: $t('不支持修改'),
        disabled: !isEdit,
      }"
      class="inline-block">
      <BkInput
        v-model="modelValue.max"
        :disabled="isEdit"
        :max="10000000"
        :min="Number(modelValue.min) || 1"
        style="width: 140px"
        type="number"
        @change="handleLimitChange('max')" />
    </span>
    <span class="item-desc">{{ $t('每秒') }}</span>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface ModelValue {
    max: number | string;
    min: number | string;
  }

  interface Props {
    isEdit: boolean;
  }

  withDefaults(defineProps<Props>(), {
    isEdit: false,
  });
  const modelValue = defineModel<ModelValue>({ required: true });

  const { t } = useI18n();

  const qpsRules = [
    {
      required: true,
      validator: (value: { max: number; min: number }) => value.max > 0 && value.min > 0,
      message: t('请输入xx', ['QPS']),
    },
  ];

  const handleLimitChange = (type: 'min' | 'max') => {
    const minValue = Number(modelValue.value.min);
    const maxValue = Number(modelValue.value.max);

    if (!minValue || !maxValue) {
      return;
    }

    if (type === 'min' && minValue > maxValue) {
      modelValue.value.min = maxValue;
      return;
    }

    if (type === 'max' && minValue > maxValue) {
      modelValue.value.max = minValue;
    }
  };
</script>

<style lang="less" scoped>
  .item-desc {
    padding: 0 12px;
    font-size: 12px;
  }
</style>
