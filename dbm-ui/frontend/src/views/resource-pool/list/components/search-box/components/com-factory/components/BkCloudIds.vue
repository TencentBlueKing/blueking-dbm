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
    filterable
    :input-search="false"
    :loading="isLoading"
    :model-value="defaultValue"
    multiple
    multiple-mode="tag"
    :placeholder="t('请选择管控区域')"
    @change="handleChange">
    <BkOption
      v-for="(item) in data"
      :key="item.bk_cloud_id"
      :label="item.bk_cloud_name"
      :value="`${item.bk_cloud_id}`" />
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getCloudList } from '@services/ip';

  interface Props {
    defaultValue?: number[]
  }
  interface Emits {
    (e: 'change', value: Props['defaultValue']): void
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();
  defineOptions({
    inheritAttrs: false,
  });
  const { t } = useI18n();

  const {
    loading: isLoading,
    data,
  } = useRequest(getCloudList, {
    initialData: [],
  });

  const handleChange = (value: Props['defaultValue']) => {
    emits('change', value);
  };
</script>

