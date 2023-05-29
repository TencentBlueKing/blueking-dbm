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
    :label="$t('管控区域')"
    property="details.bk_cloud_id"
    required>
    <BkSelect
      :allow-empty-values="[0]"
      class="item-input"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading"
      :model-value="modelValue"
      @change="handleChange">
      <BkOption
        v-for="item in cloudList"
        :key="item.bk_cloud_id"
        :label="item.bk_cloud_name"
        :value="item.bk_cloud_id" />
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { getCloudList } from '@services/ip';
  import type { CloudAreaInfo } from '@services/types/ip';

  interface Props {
    modelValue: number | string
  }
  interface Emits {
    (e: 'update:modelValue', value: number): void
    (e: 'change', value: { id: number | string, name: string }): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const cloudList = shallowRef<CloudAreaInfo[]>([]);
  const isLoading = ref(true);

  const emitCloudInfo = (id: number | string) => {
    const cloudInfo = {
      id: '' as string | number,
      name: '',
    };
    if (id !== '' && Number(id) >= 0) {
      const info = cloudList.value.find(item => item.bk_cloud_id === Number(id));
      if (info) {
        cloudInfo.id = info.bk_cloud_id;
        cloudInfo.name = info.bk_cloud_name;
      }
    }
    emits('change', cloudInfo);
  };

  const handleChange = (value: number) => {
    emits('update:modelValue', value);
  };

  watch(() => props.modelValue, (value: number | string) => {
    emitCloudInfo(value);
  });

  getCloudList()
    .then((data) => {
      cloudList.value = data;

      const { modelValue } = props;
      if (modelValue !== '' && Number(modelValue) >= 0) {
        emitCloudInfo(Number(modelValue));
      }
    })
    .finally(() => {
      isLoading.value = false;
    });
</script>

