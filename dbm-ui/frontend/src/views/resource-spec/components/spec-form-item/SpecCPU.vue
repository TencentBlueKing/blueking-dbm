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
  <div class="spec-cpu spec-form-item">
    <div class="spec-form-item__label">
      CPU
    </div>
    <div class="spec-form-item__content">
      <BkFormItem
        property="cpu.min"
        required>
        <span
          v-bk-tooltips="{
            content: $t('不支持修改'),
            disabled: !isEdit
          }"
          class="inline-block">
          <BkInput
            v-model="min"
            :disabled="isEdit"
            :max="256"
            :min="1"
            :show-control="false"
            style="width: 80px;"
            type="number"
            @change="handleLimitChange('min')" />
        </span>
      </BkFormItem>
      <span class="spec-form-item__desc">{{ $t('至') }}</span>
      <BkFormItem
        property="cpu.max"
        required>
        <span
          v-bk-tooltips="{
            content: $t('不支持修改'),
            disabled: !isEdit
          }"
          class="inline-block">
          <BkInput
            v-model="max"
            :disabled="isEdit"
            :max="256"
            :min="1"
            :show-control="false"
            style="width: 80px;"
            type="number"
            @change="handleLimitChange('max')" />
        </span>
      </BkFormItem>
      <span class="spec-form-item__desc">{{ $t('核') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    modelValue: {
      max: number | string,
      min: number | string,
    },
    isEdit: boolean
  }

  interface Emits {
    (e: 'update:modelValue', value: Props['modelValue']): void
  }

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
  });
  const emits = defineEmits<Emits>();

  const max = ref(props.modelValue.max);
  const min = ref(props.modelValue.min);

  watch([min, max], () => {
    emits('update:modelValue', { max: Number(max.value), min: Number(min.value) });
  });

  const handleLimitChange = (type: 'min' | 'max') => {
    const minValue = Number(min.value);
    const maxValue = Number(max.value);

    if (!minValue || !maxValue) return;

    if (type === 'min' && minValue > maxValue) {
      min.value = maxValue;
      return;
    }

    if (type === 'max' && minValue > maxValue) {
      max.value = min.value;
    }
  };
</script>

<style lang="less" scoped>
  @import "./specFormItem.less";
</style>
