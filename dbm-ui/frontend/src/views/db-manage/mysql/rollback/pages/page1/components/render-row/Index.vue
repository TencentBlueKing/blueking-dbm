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
  <tr>
    <FixedColumn fixed="left">
      <RenderCluster
        ref="clusterRef"
        :model-value="localClusterData"
        :unique="rollbackClusterType === RollbackClusterTypes.BUILD_INTO_METACLUSTER"
        @change="handleClusterChange" />
    </FixedColumn>
    <template v-if="showHostColumn">
      <td style="padding: 0">
        <RenderHostSource
          ref="hostSourceRef"
          :model-value="localHostSource"
          @change="handleHostSourceChange" />
      </td>
      <td style="padding: 0">
        <RenderHostInputSelect
          ref="hostRef"
          :cluster-data="localClusterData"
          :host-data="[data.rollbackHost]"
          single />
      </td>
    </template>
    <td
      v-if="showTargetClusterColumn"
      style="padding: 0">
      <RenderClusterInputSelect
        ref="targetClustersRef"
        :source-cluster-id="localClusterData.id"
        :target-cluster-id="data.targetClusterId" />
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
    <template v-if="showDbIgnoreColumn">
      <td style="padding: 0">
        <RenderDbName
          ref="databasesRef"
          check-not-exist
          :cluster-id="localClusterData.id"
          :init-value="['*']"
          :model-value="data.databases" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="databasesIgnoreRef"
          :allow-asterisk="false"
          :cluster-id="localClusterData.id"
          :model-value="data.databasesIgnore"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="tablesRef"
          :cluster-id="localClusterData.id"
          :init-value="['*']"
          :model-value="data.tables" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="tablesIgnoreRef"
          :allow-asterisk="false"
          :cluster-id="localClusterData.id"
          :model-value="data.tablesIgnore"
          :required="false" />
      </td>
    </template>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>

<script lang="ts">
  import { random } from '@utils';

  /**
   * MySql 定点回档类型
   */
  enum RollbackClusterTypes {
    BUILD_INTO_NEW_CLUSTER = 'BUILD_INTO_NEW_CLUSTER',
    BUILD_INTO_EXIST_CLUSTER = 'BUILD_INTO_EXIST_CLUSTER',
    BUILD_INTO_METACLUSTER = 'BUILD_INTO_METACLUSTER',
  }

  /**
   * MySql 定点回档主机信息
   */
  interface RollbackHost {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  export interface IDataRow {
    rowKey: string;
    clusterData: {
      id: number;
      domain: string;
      cloudId?: number;
      cloudName?: string;
      clusterType?: string;
    };
    targetClusterId?: number;
    rollbackHost: RollbackHost;
    backupSource: string;
    rollbackType: string;
    backupid?: string;
    rollbackTime?: string;
    databases: string[];
    databasesIgnore?: string[];
    tables: string[];
    tablesIgnore?: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData || {
      id: 0,
      domain: '',
    },
    targetClusterId: data.targetClusterId,
    rollbackHost: data.rollbackHost || {
      ip: '',
      bk_host_id: 0,
      bk_cloud_id: 0,
      bk_biz_id: 0,
    },
    backupSource: data.backupSource || BackupSources.REMOTE,
    rollbackType: data.rollbackType || BackupTypes.BACKUPID,
    backupid: data.backupid || '',
    rollbackTime: data.rollbackTime || '',
    databases: data.databases || ['*'],
    databasesIgnore: data.databasesIgnore,
    tables: data.tables || ['*'],
    tablesIgnore: data.tablesIgnore,
  });

  interface Props {
    rollbackClusterType: RollbackClusterTypes;
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: IDataRow[]): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    validator: (field: keyof IDataRow) => void;
    getValue: () => Promise<any>;
  }
</script>
<script setup lang="ts">
  import { ref, watch } from 'vue';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  import RenderMode, { BackupTypes } from './components/render-mode/Index.vue';
  import RenderBackup, { BackupSources } from './components/RenderBackup.vue';
  import RenderCluster from './components/RenderCluster.vue';
  import RenderClusterInputSelect from './components/RenderClusterInputSelect.vue';
  import RenderHostInputSelect from './components/RenderHostInputSelect.vue';
  import RenderHostSource from './components/RenderHostSource.vue';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const hostSourceRef = ref<InstanceType<typeof RenderHostSource>>();
  const hostRef = ref<InstanceType<typeof RenderHostInputSelect>>();
  const targetClustersRef = ref<InstanceType<typeof RenderClusterInputSelect>>();
  const backupSourceRef = ref<InstanceType<typeof RenderBackup>>();
  const modeRef = ref<InstanceType<typeof RenderMode>>();
  const databasesRef = ref<InstanceType<typeof RenderDbName>>();
  const databasesIgnoreRef = ref<InstanceType<typeof RenderDbName>>();
  const tablesRef = ref<InstanceType<typeof RenderTableName>>();
  const tablesIgnoreRef = ref<InstanceType<typeof RenderTableName>>();

  const localHostSource = ref('idle');
  const localClusterData = ref<IDataRow['clusterData']>({
    id: 0,
    domain: '',
  });
  const localBackupSource = ref(BackupSources.REMOTE);

  const configMap = {
    [RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER]: ['host', 'dbTableIgnore'],
    [RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER]: ['targetCluster', 'dbTableIgnore'],
    [RollbackClusterTypes.BUILD_INTO_METACLUSTER]: [] as string[],
  };

  const showColumn = (column: string) => computed(() => configMap[props.rollbackClusterType].includes(column));

  const showHostColumn = showColumn('host');
  const showTargetClusterColumn = showColumn('targetCluster');
  const showDbIgnoreColumn = showColumn('dbTableIgnore');

  const handleClusterChange = (data: IDataRow['clusterData']) => {
    localClusterData.value = data;
  };

  const handleHostSourceChange = (value: string) => {
    localHostSource.value = value;
  };

  const handleBackupSourceChange = (value: BackupSources) => {
    localBackupSource.value = value;
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

  const getNewClusterRowData = () =>
    Promise.all([
      clusterRef.value!.getValue(),
      hostRef.value!.getValue(),
      backupSourceRef.value!.getValue(),
      modeRef.value!.getValue(),
      databasesRef.value!.getValue('databases'),
      tablesRef.value!.getValue('tables'),
      databasesIgnoreRef.value!.getValue('databases_ignore'),
      tablesIgnoreRef.value!.getValue('tables_ignore'),
    ]).then(
      ([
        clusterData,
        hostData,
        backupSourceData,
        modeData,
        databasesData,
        tablesData,
        databasesIgnoreData,
        tablesIgnoreData,
      ]) => ({
        ...clusterData,
        rollback_host: { ...hostData.hosts[0] },
        ...backupSourceData,
        ...modeData,
        ...databasesData,
        ...tablesData,
        ...databasesIgnoreData,
        ...tablesIgnoreData,
      }),
    );

  const getExistClusterRowData = () =>
    Promise.all([
      clusterRef.value!.getValue(),
      targetClustersRef.value!.getValue(),
      backupSourceRef.value!.getValue(),
      modeRef.value!.getValue(),
      databasesRef.value!.getValue('databases'),
      tablesRef.value!.getValue('tables'),
      databasesIgnoreRef.value!.getValue('databases_ignore'),
      tablesIgnoreRef.value!.getValue('tables_ignore'),
    ]).then(
      ([
        clusterData,
        tagetClusterData,
        backupSourceData,
        modeData,
        databasesData,
        tablesData,
        databasesIgnoreData,
        tablesIgnoreData,
      ]) => ({
        ...clusterData,
        ...tagetClusterData,
        ...backupSourceData,
        ...modeData,
        ...databasesData,
        ...tablesData,
        ...databasesIgnoreData,
        ...tablesIgnoreData,
      }),
    );

  const getMetaClusterRowData = () =>
    Promise.all([clusterRef.value!.getValue(), backupSourceRef.value!.getValue(), modeRef.value!.getValue()]).then(
      ([clusterData, backupSourceData, modeData]) => ({
        ...clusterData,
        ...backupSourceData,
        ...modeData,
        target_cluster_id: clusterData.cluster_id,
        databases: ['*'],
        databases_ignore: [],
        tables: ['*'],
        tables_ignore: [],
      }),
    );

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      localBackupSource.value = props.data.backupSource as BackupSources;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    validator(field: keyof IDataRow) {
      switch (field) {
        case 'databases':
          databasesRef.value!.getValue('databases');
          break;
        case 'tables':
          tablesRef.value!.getValue('tables');
          break;
        case 'databasesIgnore':
          databasesIgnoreRef.value!.getValue('databases_ignore');
          break;
        case 'tablesIgnore':
          tablesIgnoreRef.value!.getValue('tables_ignore');
          break;
        default:
          break;
      }
    },
    getValue() {
      if (props.rollbackClusterType === RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER) {
        return getNewClusterRowData();
      }
      if (props.rollbackClusterType === RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER) {
        return getExistClusterRowData();
      }
      return getMetaClusterRowData();
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
