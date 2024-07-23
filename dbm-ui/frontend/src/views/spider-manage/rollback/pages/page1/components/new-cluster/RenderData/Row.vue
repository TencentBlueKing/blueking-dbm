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
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :model-value="localClusterData"
          :placeholder="t('请输入集群')"
          @change="handleClusterChange" />
      </td>
      <td style="padding: 0">
        <RenderHostSource
          ref="hostSourceRef"
          :model-value="localHostSource"
          @change="handleHostSourceChange" />
      </td>
      <td style="padding: 0">
        <!-- 存储层 -->
        <RenderHostInputSelect
          ref="remoteHostRef"
          :cluster-data="localClusterData" />
      </td>
      <td style="padding: 0">
        <!-- 接入层 -->
        <RenderHostInputSelect
          ref="spiderHostRef"
          :cluster-data="localClusterData"
          single />
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
      <td style="padding: 0">
        <RenderDbName
          ref="databasesRef"
          :cluster-id="localClusterData!.id"
          disabled-model-value-init
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
          disabled-model-value-init
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
  import { ClusterTypes } from '@common/const';

  import { random } from '@utils';

  import { BackupSources, BackupTypes, selectList } from '../../common/const';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId?: number;
      cloudName?: string;
    };
    rollbackHost: {
      // 接入层
      spiderHost?: {
        ip: string;
        bk_host_id: number;
        bk_cloud_id: number;
        bk_biz_id: number;
      };
      // 存储层
      remoteHosts?: {
        ip: string;
        bk_host_id: number;
        bk_cloud_id: number;
        bk_biz_id: number;
      }[];
    };
    backupSource: BackupSources;
    rollbackType: BackupTypes;
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
    rollbackHost: data.rollbackHost || {
      spiderHost: {
        ip: '',
        bk_host_id: 0,
        bk_cloud_id: 0,
        bk_biz_id: 0,
      },
      remoteHosts: [],
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
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/mysql/common/edit-field/TableName.vue';
  import RenderMode from '@views/mysql/rollback/pages/page1/components/common/render-mode/Index.vue';
  import RenderBackup from '@views/mysql/rollback/pages/page1/components/common/RenderBackup.vue';
  import RenderCluster from '@views/mysql/rollback/pages/page1/components/common/RenderCluster.vue';
  import RenderHostInputSelect from '@views/mysql/rollback/pages/page1/components/common/RenderHostInputSelect.vue';
  import RenderHostSource from '@views/mysql/rollback/pages/page1/components/common/RenderHostSource.vue';

  interface Props {
    data: IDataRow;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clusterRef = ref();
  const hostSourceRef = ref();
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
  const localBackupSource = ref(BackupSources.REMOTE);

  const handleClusterChange = (data: IDataRow['clusterData']) => {
    localClusterData.value = data;
  };

  const handleHostSourceChange = (value: string) => {
    localHostSource.value = value;
  };

  const handleBackupSourceChange = (value: string) => {
    localBackupSource.value = value as BackupSources;
  };

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      localBackupSource.value = props.data.backupSource;
    },
    {
      immediate: true,
      deep: true,
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
