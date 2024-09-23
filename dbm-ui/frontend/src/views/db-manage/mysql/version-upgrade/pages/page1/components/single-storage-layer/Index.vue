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
    <div class="mb-24">
      <RenderTable>
        <template #default>
          <RenderTableHeadColumn
            fixed="left"
            :min-width="300"
            :width="350">
            <span>{{ t('目标集群') }}</span>
            <template #append>
              <BatchOperateIcon
                class="ml-4"
                @click="handleShowMasterBatchSelector" />
            </template>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn :width="220">
            <span>{{ t('当前版本') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn :width="220">
            <span>{{ t('目标版本') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            fixed="right"
            :required="false"
            :width="100">
            {{ t('操作') }}
          </RenderTableHeadColumn>
        </template>
        <template #data>
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :removeable="tableData.length < 2"
            @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
            @cluster-input-finish="(domainObj: TendbSingleModel | null) => handleChangeCluster(index, domainObj)"
            @remove="handleRemove(index)" />
        </template>
      </RenderTable>
      <TicketRemark v-model="localRemark" />
      <ClusterSelector
        v-model:is-show="isShowClusterSelector"
        :cluster-types="[ClusterTypes.TENDBSINGLE]"
        :selected="selectedClusters"
        @change="handelClusterChange" />
    </div>
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
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbSingleModel from '@services/model/mysql/tendbsingle';
  import { createTicket } from '@services/source/ticket';

  // import { useTicketCloneInfo } from '@hooks';
  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import BatchOperateIcon from '@views/db-manage/common/batch-operate-icon/Index.vue';
  import type { InfoItem } from '@views/db-manage/redis/db-data-copy/pages/page1/Index.vue';

  import RenderDataRow, { createRowData, type IDataRow } from './Row.vue';

  interface Props {
    tableList: IDataRow[];
    remark: string;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem[]>;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const rowRefs = ref();
  const isSubmitting = ref(false);
  const localRemark = ref('');

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbSingleModel> }>({ [ClusterTypes.TENDBSINGLE]: [] });

  watch(
    () => props.tableList,
    () => {
      tableData.value = props.tableList.length > 0 ? props.tableList : [createRowData()];
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.remark,
    () => {
      localRemark.value = props.remark;
    },
    {
      immediate: true,
    },
  );

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    if (removeItem.clusterData) {
      const { domain } = removeItem.clusterData;
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBSINGLE];
      selectedClusters.value[ClusterTypes.TENDBSINGLE] = clustersArr.filter((item) => item.master_domain !== domain);
    }
    tableData.value.splice(index, 1);
  };

  const generateTableRow = (item: TendbSingleModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    clusterData: {
      domain: item.master_domain,
      clusterId: item.id,
      clusterType: item.cluster_type,
      currentVersion: item.major_version,
      packageVersion: item.masters[0].version,
      moduleName: item.db_module_name,
      cloudId: item.bk_cloud_id,
    },
  });

  // 批量选择
  const handelClusterChange = async (selected: Record<string, TendbSingleModel[]>) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.TENDBSINGLE];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateTableRow(item);
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domainObj: TendbSingleModel | null) => {
    if (domainObj) {
      const row = generateTableRow(domainObj);
      tableData.value[index] = row;
      domainMemo[domainObj.master_domain] = true;
      selectedClusters.value[ClusterTypes.TENDBSINGLE].push(domainObj);
    }
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
      await createTicket({
        ticket_type: TicketTypes.MYSQL_LOCAL_UPGRADE,
        remark: localRemark.value,
        details: {
          infos,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'MySQLVersionUpgrade',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    localRemark.value = '';
    domainMemo = {};
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    window.changeConfirm = false;
  };

  defineExpose<Exposes>({
    getValue: () =>
      Promise.all<InfoItem[]>(rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue())),
  });
</script>
