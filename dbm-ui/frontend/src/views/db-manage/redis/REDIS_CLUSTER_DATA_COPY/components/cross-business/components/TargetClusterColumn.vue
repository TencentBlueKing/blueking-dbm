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
  <EditableColumn
    field="dst_cluster"
    :label="t('目标集群')"
    required
    :width="200">
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      filterable
      :list="list"
      @change="handleChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRedisListByBizId } from '@services/source/redis';

  interface Props {
    bizId: number;
    srcClusterId?: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>();
  const clusterName = defineModel<string>('clusterName');

  const { t } = useI18n();

  const list = computed(() =>
    (data.value?.results || [])
      .map((item) => ({
        label: item.master_domain,
        value: item.id,
      }))
      .filter((item) => item.value !== props.srcClusterId),
  );

  const { data, run } = useRequest(getRedisListByBizId, {
    manual: true,
  });

  watch(
    () => props.bizId,
    () => {
      if (props.bizId > 0) {
        run({
          bk_biz_id: props.bizId,
          limit: -1,
          offset: 0,
        });
      }
    },
  );

  const handleChange = (value: number) => {
    const clusterItem = (data.value?.results || []).find((item) => item.id === value);
    clusterName.value = clusterItem?.master_domain || '';
  };
</script>
