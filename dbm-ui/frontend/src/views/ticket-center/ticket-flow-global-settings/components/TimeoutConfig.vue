<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="timeout-config-input">
    <BkRadioGroup
      :disabled="disabled"
      :model-value="mode"
      @change="handleModeChange">
      <BkRadio label="never">{{ t('永不自动终止') }}</BkRadio>
      <BkRadio label="custom">{{ t('等待达到') }}</BkRadio>
    </BkRadioGroup>
    <DbInput
      :disabled="disabled || mode !== 'custom'"
      :max="2160"
      :min="1"
      :model-value="hours"
      :placeholder="t('1～2160')"
      style="width: 140px"
      :suffix="t('小时')"
      type="number"
      @update:model-value="handleHoursChange" />
    <span>{{ t('后自动终止') }}</span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    disabled?: boolean;
  }

  type Emits = (e: 'change') => void;

  withDefaults(defineProps<Props>(), {
    disabled: false,
  });
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number | undefined>();

  const { t } = useI18n();
  const mode = ref('');
  const hours = ref('');
  const valid = computed(() => /^\d+$/.test(hours.value) && Number(hours.value) >= 1 && Number(hours.value) <= 2160);

  // 只在外部值实际变化时回填，输入校验失败时保留用户输入。
  watch(
    modelValue,
    (value) => {
      if (value === -1) {
        mode.value = 'never';
      } else if (value !== undefined) {
        mode.value = 'custom';
        hours.value = String(value);
      }
    },
    { immediate: true },
  );

  const handleModeChange = (value: string | number | boolean) => {
    mode.value = String(value);
    modelValue.value = mode.value === 'never' ? -1 : valid.value ? Number(hours.value) : undefined;
    emits('change');
  };

  const handleHoursChange = (value: string | number) => {
    hours.value = String(value);
    modelValue.value = valid.value ? Number(hours.value) : undefined;
    emits('change');
  };
</script>

<style lang="less" scoped>
  .timeout-config-input {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 12px;

  }
</style>
