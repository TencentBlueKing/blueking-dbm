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
    ref="columnRef"
    :append-rules="rules"
    field="source_mode"
    :label="t('数据源')"
    :min-width="200"
    required>
    <BkSelect
      v-model="sourceMode"
      :clearable="false">
      <BkOption
        :label="t('在线集群')"
        value="cluster" />
      <BkOption
        :label="t('备份单据')"
        value="backup_ticket" />
    </BkSelect>
    <BkSelect
      v-if="sourceMode === 'backup_ticket'"
      v-model="backupTicketId"
      class="mt-8"
      :clearable="false"
      :disabled="!sourceCluster.id"
      filterable
      :loading="loading"
      :placeholder="sourceCluster.id ? t('请选择备份单据') : t('请先选择源集群')">
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
    sourceCluster: {
      cluster_type: string;
      id: number;
    };
  }

  const props = defineProps<Props>();

  const sourceMode = defineModel<'backup_ticket' | 'cluster'>('sourceMode', {
    required: true,
  });
  const backupTicketId = defineModel<number | undefined>('backupTicketId', {
    required: true,
  });

  const { t } = useI18n();

  const columnRef = useTemplateRef('columnRef');
  const options = ref<TicketBackupLog[]>([]);

  const rules = [
    {
      message: t('请选择备份单据'),
      trigger: 'change',
      validator: () => sourceMode.value !== 'backup_ticket' || Boolean(backupTicketId.value),
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

  const formatLabel = (item: TicketBackupLog) =>
    `#${item.ticket_id} ${item.ticket_type} ${item.create_at || ''}`.trim();

  watch(sourceMode, (mode) => {
    if (mode !== 'backup_ticket') {
      backupTicketId.value = undefined;
    }
    columnRef.value?.validate();
  });

  watch(backupTicketId, () => {
    columnRef.value?.validate();
  });

  watch(
    () => [props.sourceCluster.id, props.sourceCluster.cluster_type] as const,
    ([clusterId, clusterType], previous) => {
      const prevId = previous?.[0];
      if (prevId !== undefined && prevId !== clusterId) {
        backupTicketId.value = undefined;
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
