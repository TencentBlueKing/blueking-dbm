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
          @change="handleClusterChange"
          @input-create="handleCreate" />
      </td>
      <td style="padding: 0">
        <RenderBackup
          ref="backupSourceRef"
          :list="selectList.backupSource"
          :model-value="localBackupSource"
          @change="handleBackupSourceChange" />
      </td>
      <td style="padding: 0">
        <RenderMode
          ref="modeRef"
          :backup-source="localBackupSource"
          :backupid="data.backupid"
          :cluster-id="localClusterData!.id"
          :rollback-time="data.rollbackTime" />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderMode from '@views/mysql/rollback/pages/page1/components/common/render-mode/Index.vue';
  import RenderBackup from '@views/mysql/rollback/pages/page1/components/common/RenderBackup.vue';
  import RenderCluster from '@views/mysql/rollback/pages/page1/components/common/RenderCluster.vue';

  import { BackupSources, selectList } from '../../common/const';
  import { createRowData, type IDataRow } from '../Index.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const backupSourceRef = ref<InstanceType<typeof RenderBackup>>();
  const modeRef = ref<InstanceType<typeof RenderMode>>();

  const localClusterData = ref<IDataRow['clusterData']>({
    id: 0,
    domain: '',
  });
  const localBackupSource = ref(BackupSources.REMOTE);

  const handleBackupSourceChange = (value: string) => {
    localBackupSource.value = value as BackupSources;
  };

  const handleClusterChange = (data?: IDataRow['clusterData']) => {
    localClusterData.value = data;
  };

  const handleCreate = (list: Array<string>) => {
    emits(
      'add',
      list.map((domain) =>
        createRowData({
          clusterData: {
            id: 0,
            domain,
          },
        }),
      ),
    );
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value!.getValue(),
        backupSourceRef.value!.getValue(),
        modeRef.value!.getValue(),
      ]).then(([clusterData, targetClustersData, modeData]) => ({
        ...clusterData,
        ...targetClustersData,
        ...modeData,
        target_cluster_id: clusterData.cluster_id,
        databases: ['*'],
        databases_ignore: [],
        tables: ['*'],
        tables_ignore: [],
      }));
    },
  });
</script>
