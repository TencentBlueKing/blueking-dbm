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
  <div class="render-data">
    <RenderTable>
      <RenderTableHeadColumn>
        <span>{{ $t('源集群') }}</span>
        <template #append>
          <BkPopover
            :content="$t('批量添加')"
            theme="dark">
            <span
              class="batch-edit-btn"
              @click="handleShowMasterBatchSelector">
              <DbIcon type="batch-host-select" />
            </span>
          </BkPopover>
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('目标集群') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('访问密码') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('包含Key') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('排除Key') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :required="false"
        :width="120">
        {{ $t('操作') }}
      </RenderTableHeadColumn>
      <template #data>
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :cluster-list="clusterList"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @on-cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </template>
    </RenderTable>
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :tab-list="clusterSelectorTabList"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="ts">
  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';
  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/redis/common/render-table/Index.vue';
  import { getClusterInfo } from '@views/redis/common/utils';

  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type TableRealRowData,
  } from './Row.vue';

  import RedisModel from '@/services/model/redis/redis';

  interface Props {
    clusterList: string[];
  }

  interface Exposes {
    getValue: () => Promise<TableRealRowData[]>
  }

  defineProps<Props>();

  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const rowRefs = ref();

  const clusterSelectorTabList = [ClusterTypes.REDIS];

  // 集群域名是否已存在表格的映射表
  const domainMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };

  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
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
    const removeItem = dataList[index];
    const { srcCluster } = removeItem;
    dataList.splice(index, 1);
    delete domainMemo[srcCluster];
  };


  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow[] = [];
    const domains = list.map(item => item.immute_domain);
    const clustersInfo = await getClusterInfo(domains);
    clustersInfo.forEach((item) => {
      const domain = item.cluster.immute_domain;
      if (!domainMemo[domain]) {
        const row: IDataRow = {
          rowKey: item.cluster.immute_domain,
          isLoading: false,
          srcCluster: item.cluster.immute_domain,
          password: '',
          targetCluster: '',
          includeKey: ['*'],
          excludeKey: [],
        };
        newList.push(row);
        domainMemo[domain] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    const ret = await getClusterInfo(domain);
    if (ret) {
      const data = ret[0];
      const row: IDataRow = {
        rowKey: data.cluster.immute_domain,
        isLoading: false,
        srcCluster: data.cluster.immute_domain,
        password: '',
        targetCluster: '',
        includeKey: ['*'],
        excludeKey: [],
      };
      tableData.value[index] = row;
      domainMemo[domain] = true;
    }
  };

  defineExpose<Exposes>({
    getValue: () => Promise.all<TableRealRowData[]>(rowRefs.value.map((item: {
      getValue: () => Promise<TableRealRowData>
    }) => item.getValue())),
  });
</script>
<style lang="less">
.render-data {
  .batch-edit-btn {
    margin-left: 4px;
    color: #3a84ff;
    cursor: pointer;
  }
}

</style>
