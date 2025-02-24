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
        :model-value="data.clusterData"
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderText
        :data="data.master"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderSlave
        ref="slaveRef"
        :data="data.slaves"
        :list="slaveInstances" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="dbPatternsRef"
        check-not-exist
        :cluster-id="localClusterId"
        :model-value="data.dbPatterns" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        :allow-asterisk="false"
        :cluster-id="localClusterId"
        :model-value="data.ignoreDbs"
        :required="false"
        @change="handleIgnoreDbsChange" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablePatternsRef"
        :cluster-id="localClusterId"
        :model-value="data.tablePatterns" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="ignoreTablesRef"
        :allow-asterisk="false"
        :cluster-id="localClusterId"
        :model-value="data.ignoreTables"
        :required="false" />
    </td>
    <OperateColumn
      :removeable="removeable"
      :show-add="false"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import TendbhaModel from '@services/model/mysql/tendbha';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  type ResourceItemInstInfo = TendbhaModel['masters'][number];

  export interface IDataRow {
    clusterData?: {
      domain: string;
      id: number;
    };
    dbPatterns: string[];
    ignoreDbs: string[];
    ignoreTables: string[];
    isLoading: boolean;
    master: string;
    masterInstance: ResourceItemInstInfo;
    rowKey: string;
    slaveList: ResourceItemInstInfo[];
    slaves: string[];
    tablePatterns: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    clusterData: data.clusterData,
    dbPatterns: data.dbPatterns ?? [],
    ignoreDbs: data.ignoreDbs ?? [],
    ignoreTables: data.ignoreTables ?? [],
    isLoading: false,
    master: data.master ?? '',
    masterInstance: data.masterInstance ?? createInstanceData(),
    rowKey: random(),
    slaveList: data.slaveList ?? [],
    slaves: data.slaves ?? [],
    tablePatterns: data.tablePatterns ?? [],
  });

  export const createInstanceData = (): ResourceItemInstInfo => ({
    bk_biz_id: 0,
    bk_cloud_id: 0,
    bk_host_id: 0,
    bk_instance_id: 0,
    instance: '',
    ip: '',
    name: '',
    phase: '',
    port: 0,
    spec_config: {
      id: 0,
    },
    status: 'running',
    version: '',
  });

  export type IDataRowBatchKey = keyof Pick<IDataRow, 'dbPatterns' | 'ignoreDbs' | 'tablePatterns' | 'ignoreTables'>;
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderCluster from '@views/db-manage/mysql/common/edit-field/ClusterName.vue';
  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  // import RenderIgnoreTables from './RenderIgnoreTables.vue';
  import RenderSlave from './RenderSlave.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const slaveRef = ref<InstanceType<typeof RenderSlave>>();
  const dbPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const tablePatternsRef = ref<InstanceType<typeof RenderTableName>>();
  const ignoreTablesRef = ref<InstanceType<typeof RenderTableName>>();
  const localRowData = ref<IDataRow>(createRowData());
  const localClusterId = ref(0);

  const slaveInstances = computed(() => props.data.slaveList.map((item) => item.instance));

  watch(
    () => props.data,
    (data) => {
      if (data) {
        localClusterId.value = props.data.clusterData?.id ?? 0;
        localRowData.value = props.data;
      }
    },
    {
      immediate: true,
    },
  );

  const handleIgnoreDbsChange = (value: string[]) => {
    localRowData.value.ignoreDbs = value;
  };

  const handleClusterIdChange = (clusterId: number) => {
    emits('clusterInputFinish', clusterId);
    localClusterId.value = clusterId;
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  const formatInstance = (inst: ResourceItemInstInfo) => ({
    bk_biz_id: inst.bk_biz_id,
    bk_cloud_id: inst.bk_cloud_id,
    bk_host_id: inst.bk_host_id,
    ip: inst.ip,
    port: inst.port,
  });

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue();
      return Promise.all([
        slaveRef.value!.getValue(),
        dbPatternsRef.value!.getValue('db_patterns'),
        tablePatternsRef.value!.getValue('table_patterns'),
        ignoreDbsRef.value!.getValue('ignore_dbs'),
        ignoreTablesRef.value!.getValue('ignore_tables'),
      ]).then(([slaveList, dbPatterns, tablePatterns, ignoreDbs, ignoreTables]) => {
        const slavesMap = props.data.slaveList.reduce<Record<string, IDataRow['slaveList'][number]>>(
          (results, item) => {
            Object.assign(results, {
              [item.instance]: item,
            });
            return results;
          },
          {},
        );
        return {
          cluster_id: localClusterId.value,
          master: formatInstance(props.data.masterInstance),
          slaves: slaveList.map((inst) => formatInstance(slavesMap[inst])),
          ...dbPatterns,
          ...ignoreDbs,
          ...tablePatterns,
          ...ignoreTables,
        };
      });
    },
  });
</script>
