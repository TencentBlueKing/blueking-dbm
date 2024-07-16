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
  <tbody>
    <tr>
      <td style="padding: 0">
        <RenderCluster
          ref="clusterRef"
          :model-value="localClusterData"
          @change="handleClusterChange" />
      </td>
      <td style="padding: 0">
        <RenderBackup
          ref="backupSourceRef"
          :model-value="localBackupSource"
          @change="handleBackupSourceChange" />
      </td>
      <td style="padding: 0">
        <RenderMode
          ref="modeRef"
          :backup-source="localBackupSource"
          :backupid="data.backupid"
          :cluster-id="localClusterData.id"
          :rollback-time="data.rollbackTime" />
      </td>
    </tr>
  </tbody>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId?: number;
      cloudName?: string;
    };
    backupSource: string;
    rollbackupType: string;
    backupid?: string;
    rollbackTime?: string;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData || {
      id: 0,
      domain: '',
    },
    backupSource: data.backupSource || 'remote',
    rollbackupType: data.rollbackupType || 'REMOTE_AND_TIME',
    backupid: data.backupid || '',
    rollbackTime: data.rollbackTime || '',
  });
</script>
<script setup lang="ts">
  import RenderCluster from '@views/mysql/rollback/pages/page1/components/common/RenderCluster.vue';
  import RenderMode from '@views/spider-manage/rollback/pages/page1/components/common/render-mode/Index.vue';
  import RenderBackup from '@views/spider-manage/rollback/pages/page1/components/common/RenderBackup.vue';

  interface Props {
    data: IDataRow;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const clusterRef = ref();
  const modeRef = ref();

  const localClusterData = ref();
  const localRollbackuoType = ref('');
  const localBackupSource = ref('remote');

  const handleBackupSourceChange = (value: string) => {
    localBackupSource.value = value;
  };

  const handleClusterChange = (data?: IDataRow['clusterData']) => {
    localClusterData.value = data;
  };

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      localRollbackuoType.value = props.data.rollbackupType;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([clusterRef.value.getValue(), modeRef.value.getValue()]).then(([clusterData, modeData]) => ({
        ...clusterData,
        ...modeData,
        target_cluster_id: clusterData.cluster_id,
      }));
    },
  });
</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
