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
        <RenderHostSource
          ref="backupSourceRef"
          :model-value="localHostSource"
          @change="handleHostSourceChange" />
      </td>
      <td style="padding: 0">
        <!-- 存储层 -->
        <RenderHostSelector
          ref="remoteHostRef"
          :cluster-data="localClusterData"
          :cluster-id="localClusterData!.id" />
      </td>
      <td style="padding: 0">
        <!-- 接入层 -->
        <RenderHostSelector
          ref="spiderHostRef"
          :cluster-data="localClusterData"
          :cluster-id="localClusterData!.id"
          :placeholder="t('请选择主机 (1台)')"
          single />
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
          :cluster-id="localClusterData!.id"
          :rollback-time="data.rollbackTime" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="databasesRef"
          :cluster-id="localClusterData!.id"
          :model-value="data.databases" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="databasesIgnoreRef"
          :cluster-id="localClusterData!.id"
          :model-value="data.databasesIgnore"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="tablesRef"
          :cluster-id="localClusterData!.id"
          :model-value="data.tables" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="tablesIgnoreRef"
          :cluster-id="localClusterData!.id"
          :model-value="data.tablesIgnore"
          :required="false" />
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
    rollback_host: {
      // 接入层
      spider_host?: {
        ip: string;
        bk_host_id: number;
        bk_cloud_id: number;
        bk_biz_id: number;
      };
      // 存储层
      remote_hosts?: {
        ip: string;
        bk_host_id: number;
        bk_cloud_id: number;
        bk_biz_id: number;
      }[];
    };
    backupSource: string;
    rollbackupType: string;
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
    rollback_host: data.rollback_host || {
      spider_host: {
        ip: '',
        bk_host_id: 0,
        bk_cloud_id: 0,
        bk_biz_id: 0,
      },
      remote_hosts: [],
    },
    backupSource: data.backupSource || 'remote',
    rollbackupType: data.rollbackupType || 'REMOTE_AND_TIME',
    backupid: data.backupid || '',
    rollbackTime: data.rollbackTime || '',
    databases: data.databases || ['*'],
    databasesIgnore: data.databasesIgnore,
    tables: data.tables || ['*'],
    tablesIgnore: data.tablesIgnore,
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/mysql/common/edit-field/TableName.vue';
  import RenderCluster from '@views/mysql/rollback/pages/page1/components/common/RenderCluster.vue';
  import RenderMode from '@views/spider-manage/rollback/pages/page1/components/common/render-mode/Index.vue';
  import RenderBackup from '@views/spider-manage/rollback/pages/page1/components/common/RenderBackup.vue';
  import RenderHostSelector from '@views/spider-manage/rollback/pages/page1/components/common/RenderHostSelector.vue';
  import RenderHostSource from '@views/spider-manage/rollback/pages/page1/components/common/RenderHostSource.vue';

  interface Props {
    data: IDataRow;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clusterRef = ref();
  const spiderHostRef = ref();
  const remoteHostRef = ref();
  const modeRef = ref();
  const databasesRef = ref();
  const databasesIgnoreRef = ref();
  const tablesRef = ref();
  const tablesIgnoreRef = ref();
  const localClusterData = ref<IDataRow['clusterData']>({
    id: 0,
    domain: '',
  });
  const localHostSource = ref('idle');
  const localRollbackuoType = ref('');
  const localBackupSource = ref('remote');

  const handleHostSourceChange = (value: string) => {
    localHostSource.value = value;
  };

  const handleBackupSourceChange = (value: string) => {
    localBackupSource.value = value;
  };

  const handleClusterChange = (data: IDataRow['clusterData']) => {
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
      return Promise.all([
        clusterRef.value.getValue(),
        remoteHostRef.value.getValue(),
        spiderHostRef.value.getValue(),
        modeRef.value.getValue(),
        databasesRef.value.getValue('databases'),
        tablesRef.value.getValue('tables'),
        databasesIgnoreRef.value.getValue('databases_ignore'),
        tablesIgnoreRef.value.getValue('tables_ignore'),
      ]).then(
        ([
          clusterData,
          remoteHostsData,
          spiderHostData,
          modeData,
          databasesData,
          tablesData,
          databasesIgnoreData,
          tablesIgnoreData,
        ]) => ({
          ...clusterData,
          rollback_host: {
            remote_hosts: remoteHostsData.hosts,
            spider_host: spiderHostData.hosts[0],
          },
          ...modeData,
          ...databasesData,
          ...tablesData,
          ...databasesIgnoreData,
          ...tablesIgnoreData,
        }),
      );
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
