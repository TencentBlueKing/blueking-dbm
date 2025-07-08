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
  <BkSelect
    :disabled="Boolean(model.spec_id)"
    filterable
    :input-search="false"
    :model-value="defaultValue"
    :placeholder="t('请选择磁盘类型')"
    @change="handleChange">
    <BkOption
      v-for="item in dataList"
      :key="item.value"
      :label="item.label"
      :value="item.value">
      {{ item.label }}
    </BkOption>
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { searchDeviceClass } from '@services/source/ipchooser';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

  interface Props {
    defaultValue?: string;
    model: Record<string, any>;
  }

  type Emits = (e: 'change', value: Props['defaultValue']) => void;

  defineOptions({
    inheritAttrs: false,
  });

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const dataList = computed(() =>
    (data.value || [])
      .filter((item) => item !== 'ALL')
      .map((item) => ({
        label: deviceClassDisplayMap[item as DeviceClass],
        value: item,
      })),
  );

  const { data } = useRequest(searchDeviceClass);

  const handleChange = (value: Props['defaultValue']) => {
    emits('change', value);
  };
</script>
