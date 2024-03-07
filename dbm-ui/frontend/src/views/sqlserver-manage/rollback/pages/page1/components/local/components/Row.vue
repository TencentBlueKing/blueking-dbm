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
      <FixedColumn fixed="left">
        <RenderCluster
          ref="clusterRef"
          v-model="localClusterData" />
      </FixedColumn>
      <td style="padding: 0">
        <RenderMode
          ref="modeRef"
          v-model:restore-backup-file="localRestoreBackupFile"
          v-model:restore-time="localRestoreTime"
          :cluster-id="localClusterData?.id" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="dbNameRef"
          v-model="localDbName"
          check-not-exist
          :cluster-id="localClusterData?.id"
          @change="handleDbNameChange" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="ignoreDbNameRef"
          v-model="localDbIgnoreName"
          check-not-exist
          :cluster-id="localClusterData?.id"
          :required="false"
          @change="handleTargerNameChange" />
      </td>
      <td style="padding: 0">
        <RenderRename
          ref="renameDbNameRef"
          v-model:db-ignore-name="localDbIgnoreName"
          v-model:db-name="localDbName"
          :cluster-data="localClusterData"
          :restore-backup-file="localRestoreBackupFile"
          :restore-time="localRestoreTime" />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script lang="ts">
  import { ref, watch } from 'vue';

  import { queryBackupLogs } from '@services/source/sqlserver';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderDbName from '@views/sqlserver-manage/common/DbName.vue';
  import RenderMode from '@views/sqlserver-manage/common/render-mode/Index.vue';
  import RenderCluster from '@views/sqlserver-manage/common/RenderCluster.vue';

  import { random } from '@utils';

  import RenderRename from './RenderRename.vue';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number;
    };
    restoreBackupFile?: ServiceReturnType<typeof queryBackupLogs>[number];
    restoreTime: string;
    dbName: string[];
    dbIgnoreName: string[];
    renameDbName: {
      db_name: string;
      target_db_name: string;
      rename_db_name: string;
    }[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    restoreBackupFile: data.restoreBackupFile,
    restoreTime: data.restoreTime || '',
    dbName: data.dbName || [],
    dbIgnoreName: data.dbIgnoreName || [],
    renameDbName: data.renameDbName || [],
  });
</script>
<script setup lang="ts">
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
  const modeRef = ref<InstanceType<typeof RenderMode>>();
  const dbNameRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbNameRef = ref<InstanceType<typeof RenderDbName>>();
  const renameDbNameRef = ref<InstanceType<typeof RenderRename>>();

  const localClusterData = ref<IDataRow['clusterData']>();
  const localRestoreBackupFile = ref<IDataRow['restoreBackupFile']>();
  const localRestoreTime = ref<IDataRow['restoreTime']>('');
  const localDbName = ref<string[]>([]);
  const localDbIgnoreName = ref<string[]>([]);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      if (props.data.restoreBackupFile) {
        localRestoreBackupFile.value = props.data.restoreBackupFile;
      }
      if (props.data.restoreTime) {
        localRestoreTime.value = props.data.restoreTime;
      }
      localDbName.value = props.data.dbName;
      localDbIgnoreName.value = props.data.dbIgnoreName;
    },
    {
      immediate: true,
    },
  );

  const handleDbNameChange = (value: string[]) => {
    localDbName.value = value;
  };
  const handleTargerNameChange = (value: string[]) => {
    localDbIgnoreName.value = value;
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

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value!.getValue('src_cluster'),
        modeRef.value!.getValue(),
        dbNameRef.value!.getValue('db_list'),
        ignoreDbNameRef.value!.getValue('ignore_db_list'),
        renameDbNameRef.value!.getValue(),
      ]).then(([clusterData, modeData, databasesData, tablesData, dbIgnoreNameData]) => ({
        ...clusterData,
        dst_cluster: clusterData.src_cluster,
        ...modeData,
        ...databasesData,
        ...tablesData,
        ...dbIgnoreNameData,
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
