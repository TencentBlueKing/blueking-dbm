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
    field="slave.ip"
    :label="t('从库主机')"
    :loading="loading"
    :min-width="150">
    <EditableBlock
      v-model="modelValue.ip"
      :placeholder="t('自动生成')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getIntersectedSlaveMachinesFromClusters } from '@services/source/mysqlCluster';

  interface Props {
    master: {
      bk_host_id: number;
      related_clusters: {
        id: number;
      }[];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const { loading, run: getIntersectedSlaveMachines } = useRequest(getIntersectedSlaveMachinesFromClusters, {
    manual: true,
    onSuccess: (data) => {
      const [slave] = data;
      if (slave) {
        modelValue.value = {
          bk_cloud_id: slave.bk_cloud_id,
          bk_host_id: slave.bk_host_id,
          ip: slave.ip,
        };
      }
    },
  });

  watch(
    () => props.master.bk_host_id,
    () => {
      if (props.master.bk_host_id) {
        getIntersectedSlaveMachines({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: props.master.related_clusters.map((item) => item.id),
          is_stand_by: true,
        });
      } else {
        modelValue.value = {
          bk_cloud_id: 0,
          bk_host_id: 0,
          ip: '',
        };
      }
    },
    {
      immediate: true,
    },
  );
</script>
