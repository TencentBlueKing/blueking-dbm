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
    :append-rules="rules"
    :disabled-method="disabledMethod"
    field="backup_ticket_id"
    :label="t('备份单据')"
    :loading="loading"
    :min-width="220"
    :required="required">
    <BkSelect
      v-model="modelValue"
      :clearable="true"
      filterable
      :input-search="false"
      :placeholder="t('请选择备份单据')">
      <BkOption
        v-for="item in options"
        :key="item.ticket_id"
        :label="formatLabel(item)"
        :value="item.ticket_id" />
    </BkSelect>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryTicketBackupLog, type TicketBackupLog } from '@services/source/mongodbRestore';

  import { ClusterTypes } from '@common/const';

  interface Props {
    required?: boolean;
    sourceCluster: {
      cluster_type: string;
      id: number;
    };
  }

  const props = withDefaults(defineProps<Props>(), {
    required: false,
  });

  const modelValue = defineModel<number | undefined>({
    required: true,
  });

  const { t } = useI18n();

  const options = ref<TicketBackupLog[]>([]);

  const rules = [
    {
      message: t('请选择备份单据'),
      trigger: 'change',
      validator: (value: number | undefined) => !props.required || Boolean(value),
    },
  ];

  const { loading, run: fetchBackupTickets } = useRequest(queryTicketBackupLog, {
    manual: true,
    onError() {
      options.value = [];
    },
    onSuccess(data) {
      options.value = data || [];
    },
  });

  const disabledMethod = () => {
    if (!props.sourceCluster.id) {
      return t('请先选择源集群');
    }
    return '';
  };

  const formatLabel = (item: TicketBackupLog) =>
    `#${item.ticket_id} ${item.ticket_type} ${item.create_at || ''}`.trim();

  watch(
    () => [props.sourceCluster.id, props.sourceCluster.cluster_type] as const,
    ([clusterId, clusterType], previous) => {
      const prevId = previous?.[0];
      if (prevId !== undefined && prevId !== clusterId) {
        modelValue.value = undefined;
      }
      options.value = [];
      if (!clusterId || !clusterType) {
        return;
      }
      fetchBackupTickets({
        cluster_ids: [clusterId],
        cluster_type: clusterType as ClusterTypes,
      });
    },
    {
      immediate: true,
    },
  );
</script>
