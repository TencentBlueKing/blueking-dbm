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
  <div class="spec-mem spec-form-item">
    <div class="spec-form-item__label">
      {{ $t('机型') }}
    </div>
    <div class="spec-form-item__content">
      <BkFormItem
        property="device_class"
        required
        :rules="rules"
        style="width: 100%">
        <BkSelect
          v-model="localValue"
          :allow-empty-values="['']"
          filterable
          :input-search="false"
          :loading="isLoading"
          multiple
          @change="handleChange">
          <BkOption
            key="all"
            :label="t('无限制')"
            value="" />
          <BkOption
            v-for="item in deviceClassList"
            :key="item"
            :label="item"
            :value="item" />
        </BkSelect>
      </BkFormItem>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getDeviceClassList } from '@services/system-setting';

  interface Emits {
    (e: 'update:modelValue', value: string[]): void;
  }

  interface Props {
    modelValue: string[];
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref<string[] | string>(props.modelValue);
  const rules = [
    {
      required: true,
      validator: (value: string[]) => value.length > 0,
      message: t('请选择xx', [t('机型')]),
    },
  ];

  const { loading: isLoading, data: deviceClassList } = useRequest(getDeviceClassList);

  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue.length === 0) {
        localValue.value = '';
        return;
      }
      localValue.value = props.modelValue;
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('update:modelValue', localValue.value as string[]);
  };
</script>

<style lang="less" scoped>
  @import './specFormItem.less';
</style>
