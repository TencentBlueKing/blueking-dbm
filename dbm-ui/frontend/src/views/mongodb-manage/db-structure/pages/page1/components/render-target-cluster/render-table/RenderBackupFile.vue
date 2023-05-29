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
  <TableEditSelect
    ref="localBackupidRef"
    v-model="localBackupid"
    :disabled="editDisabled"
    :list="logRecordList"
    :rules="rules" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryClustersBackupLog } from '@services/source/mongodbRestore';

  import TableEditSelect from '@views/mysql/common/edit/Select.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    clusterId: number;
    clusterType: string;
  }

  interface Exposes {
    getValue: () => Promise<{ [key: number]: ClusterBackupLogs[number] }>
  }

  type ClusterBackupLogs = ServiceReturnType<typeof queryClustersBackupLog>[number]

  const props = defineProps<Props>();

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('备份记录不能为空'),
    },
  ];

  const localBackupidRef = ref<InstanceType<typeof TableEditSelect>>();
  const localBackupid = ref('');

  const logRecordList = shallowRef<{ id: string, name: string}[]>([]);

  const editDisabled = computed(() => !props.clusterId);

  let logRecordListMemo: ClusterBackupLogs = [];

  const {
    run: fetchTicketBackupLog,
  } = useRequest(queryClustersBackupLog, {
    manual: true,
    onSuccess(data) {
      if (!data[props.clusterId]) {
        return;
      }
      logRecordList.value = data[props.clusterId].map(item => ({
        id: item.file_name,
        name: `${item.role_type}${utcDisplayTime(item.end_time)}`,
      }));
      logRecordListMemo = data[props.clusterId];
    },
  });

  watch(() => props.clusterId, () => {
    if (!props.clusterId) {
      return;
    }
    fetchTicketBackupLog({
      cluster_ids: [props.clusterId],
      cluster_type: props.clusterType,
    });
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return localBackupidRef.value!.getValue()
        .then(() => {
          const backupInfo = logRecordListMemo.find(item => item.file_name === localBackupid.value)!;
          return ({
            [props.clusterId]: backupInfo,
          });
        });
    },
  });
</script>
<style lang="less" scoped>
  .render-mode {
    display: flex;

    .action-item {
      flex: 0 0 50%;
      overflow: hidden;
    }
  }

  .local-backup-select {
    position: relative;

    :deep(.table-edit-select) {
      .select-result-text {
        padding-left: 14px;
      }

      .select-placeholder {
        left: 30px;
      }
    }

    .file-flag {
      position: absolute;
      top: 14px;
      left: 8px;
      z-index: 1;
      font-size: 16px;
      color: #c4c6cc;
    }
  }
</style>
