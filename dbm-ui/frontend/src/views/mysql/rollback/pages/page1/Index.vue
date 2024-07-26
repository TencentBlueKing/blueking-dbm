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
  <BkAlert
    closable
    theme="info"
    :title="t('新建一个单节点实例_通过全备_binlog的方式_将数据库恢复到过去的某一时间点或者某个指定备份文件的状态')" />
  <div class="title-spot mt-12 mb-10">{{ t('时区') }}<span class="required" /></div>
  <TimeZonePicker style="width: 450px" />
  <div class="title-spot mt-12 mb-10">{{ t('构造类型') }}<span class="required" /></div>
  <BkRadioGroup
    v-model="rollbackClusterType"
    style="width: 450px"
    type="card"
    @change="handleReset">
    <BkRadioButton
      v-for="(item, index) in rollbackInfos"
      :key="index"
      :label="item.value">
      {{ item.label }}
    </BkRadioButton>
  </BkRadioGroup>
  <RenderData
    ref="ticketRef"
    :data="tableData"
    :rollback-cluster-type="rollbackClusterType"
    @add="handleAppend"
    @batch-edit="(obj) => handleBatchEdit(obj)"
    @remove="handleRemove"
    @show-selector="handleShowSelector"
    @submit="handleSubmit">
    <BkButton
      class="w-88"
      :loading="isSubmitting"
      theme="primary"
      @click="handleSubmit">
      {{ t('提交') }}
    </BkButton>
    <DbPopconfirm
      :confirm-handler="handleReset"
      :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
      :title="t('确认重置页面')">
      <BkButton
        class="ml8 w-88"
        :disabled="isSubmitting">
        {{ t('重置') }}
      </BkButton>
    </DbPopconfirm>
  </RenderData>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    :selected="selectedClusters"
    @change="handelClusterChange" />
</template>
<script lang="ts">
  import { random } from '@utils';

  import { BackupSources, BackupTypes } from './components/common/const';
  import type { HostDataItem } from './components/common/RenderHostInputSelect.vue';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId?: number;
      cloudName?: string;
      clusterType?: string;
    };
    targetClusterId?: number;
    rollbackHost?: HostDataItem;
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
    targetClusterId: data.targetClusterId || 0,
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
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { RollbackClusterTypes } from '@services/model/ticket/details/mysql';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import RenderData from './components/render-data/Index.vue';

  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
    onSuccess(cloneData) {
      rollbackClusterType.value = cloneData.rollback_cluster_type;
      tableData.value = cloneData.tableDataList as IDataRow[];
      window.changeConfirm = true;
    },
  });

  const rollbackInfos = {
    [RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER]: {
      value: RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER,
      label: t('构造到新集群'),
    },
    [RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER]: {
      value: RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER,
      label: t('构造到已有集群'),
    },
    [RollbackClusterTypes.BUILD_INTO_METACLUSTER]: {
      value: RollbackClusterTypes.BUILD_INTO_METACLUSTER,
      label: t('构造到原集群'),
    },
  };

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};
  const initSelected = {
    [ClusterTypes.TENDBHA]: [] as TendbhaModel[],
    [ClusterTypes.TENDBSINGLE]: [] as TendbsingleModel[],
  };

  const ticketRef = ref<InstanceType<typeof RenderData>>();
  const isShowSelector = ref(false);
  const isSubmitting = ref(false);
  const rollbackClusterType = ref<RollbackClusterTypes>(RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER);
  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> | Array<TendbsingleModel> }>(initSelected);

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData?.id;
  };

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  // 批量编辑
  const handleBatchEdit = (obj: Record<string, any>) => {
    if (!obj) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, { ...obj });
    });
  };

  // 批量选择
  const handelClusterChange = (selected: Record<string, Array<TendbhaModel> | Array<TendbsingleModel>>) => {
    selectedClusters.value = selected;
    const newList = [...selected[ClusterTypes.TENDBHA], ...selected[ClusterTypes.TENDBSINGLE]].reduce(
      (results, clusterData) => {
        const domain = clusterData.master_domain;
        if (!domainMemo[domain]) {
          const row = createRowData({
            clusterData: {
              id: clusterData.id,
              domain,
              cloudId: clusterData.bk_cloud_id,
              cloudName: clusterData.bk_biz_name,
              clusterType: clusterData.cluster_type,
            },
          });
          results.push(row);
          domainMemo[domain] = true;
        }
        return results;
      },
      [] as IDataRow[],
    );
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const rowData = dataList[index].clusterData;
    if (rowData?.domain && rowData?.clusterType) {
      delete domainMemo[rowData.domain];
      const clustersArr = selectedClusters.value[rowData.clusterType];
      selectedClusters.value[rowData.clusterType] = clustersArr.filter((item) => item.master_domain !== rowData.domain);
    }
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    ticketRef
      .value!.getValue()
      .then((infos: Record<string, string>[]) =>
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
          remark: '',
          details: {
            rollback_cluster_type: rollbackClusterType.value,
            infos,
          },
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLDBRollback',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value = initSelected;
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>
