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
  <SmartAction>
    <RenderTable
      :key="rollbackClusterType"
      class="mt16 mb-20"
      :rollback-cluster-type="rollbackClusterType"
      @batch-edit="(obj) => handleBatchEdit(obj)"
      @show-selector="handleShowSelector">
      <RenderRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        :rollback-cluster-type="rollbackClusterType"
        @add="(payload: IDataRow[]) => handleAppend(index, payload)"
        @remove="() => handleRemove(index)" />
    </RenderTable>
    <template #action>
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
    </template>
  </SmartAction>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    :selected="selectedClusters"
    @change="handelClusterChange" />
</template>
<script lang="ts">
  const enum RollbackClusterTypes {
    BUILD_INTO_NEW_CLUSTER = 'BUILD_INTO_NEW_CLUSTER',
    BUILD_INTO_EXIST_CLUSTER = 'BUILD_INTO_EXIST_CLUSTER',
    BUILD_INTO_METACLUSTER = 'BUILD_INTO_METACLUSTER',
  }

  interface Props {
    data: IDataRow[];
    rollbackClusterType: RollbackClusterTypes;
  }

  interface Exposes {
    reset: () => void;
  }
</script>
<script setup lang="ts">
  import { debounce } from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { createTicket } from '@services/source/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import { messageWarn } from '@utils';

  import RenderRow, { createRowData, type IDataRow } from './render-row/Index.vue';
  import RenderTable from './RenderTable.vue';

  const props = defineProps<Props>();

  const { t } = useI18n();

  const router = useRouter();

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};
  const initSelected = {
    [ClusterTypes.TENDBHA]: [] as TendbhaModel[],
    [ClusterTypes.TENDBSINGLE]: [] as TendbsingleModel[],
  };

  const rowRefs = ref();
  const isShowSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<IDataRow[]>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> | Array<TendbsingleModel> }>(initSelected);

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
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
    if (checkListEmpty(tableData.value)) {
      debounce(() => {
        messageWarn(t('请先添加待回档集群'));
      }, 300);
      return;
    }
    if (!obj) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, { ...obj });
    });
    const field = Object.keys(obj)[0] as keyof IDataRow;
    if (['databases', 'tables', 'databasesIgnore', 'tablesIgnore'].includes(field)) {
      nextTick(() => {
        Promise.all(rowRefs.value.map((item: { validator: (field: keyof IDataRow) => void }) => item.validator(field)));
      });
    }
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
  const handleAppend = (index: number, appendList: IDataRow[]) => {
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

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
      await createTicket({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ticket_type: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
        remark: '',
        details: {
          rollback_cluster_type: props.rollbackClusterType,
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
            ticket_id: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value = initSelected;
    domainMemo = {};
    window.changeConfirm = false;
  };

  watch(
    () => props.data,
    () => {
      tableData.value = props.data;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    reset() {
      handleReset();
    },
  });
</script>
