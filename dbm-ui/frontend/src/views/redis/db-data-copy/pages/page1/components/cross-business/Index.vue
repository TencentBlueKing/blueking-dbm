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
        <span>{{ $t('目标业务') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('目标集群') }}</span>
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
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
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
  import RedisModel from '@services/model/redis/redis';
  import RedisDSTHistoryJobModel  from '@services/model/redis/redis-dst-history-job';
  import { listClusterList } from '@services/redis/toolbox';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    LocalStorageKeys,
  } from '@common/const';

  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';
  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/redis/common/render-table/Index.vue';
  import type { CrossBusinessInfoItem } from '@views/redis/db-data-copy/pages/page1/Index.vue';

  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './Row.vue';

  interface Exposes {
    getValue: () => Promise<CrossBusinessInfoItem[]>,
    resetTable: () => void
  }

  const emits = defineEmits<{
    'change-table-available': [status: boolean]
  }>();

  const { currentBizId } = useGlobalBizs();
  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const rowRefs = ref();
  const tableAvailable = computed(() => tableData.value.findIndex(item => Boolean(item.srcCluster)) > -1);

  const clusterSelectorTabList = [ClusterTypes.REDIS];

  // 集群域名是否已存在表格的映射表
  const domainMemo = {} as Record<string, boolean>;

  watch(tableAvailable, (status) => {
    emits('change-table-available', status);
  });

  onMounted(() => {
    checkandRecoverDataListFromLocalStorage();
  });

  const checkandRecoverDataListFromLocalStorage = () => {
    const r = localStorage.getItem(LocalStorageKeys.REDIS_DB_DATA_RECORD_RECOPY);
    if (!r) {
      return;
    }
    const item = JSON.parse(r) as RedisDSTHistoryJobModel;
    tableData.value = [{
      rowKey: item.src_cluster,
      isLoading: false,
      srcCluster: item.src_cluster,
      srcClusterId: item.src_cluster_id,
      targetBusines: Number(item.dst_bk_biz_id),
      targetClusterId: item.dst_cluster_id,
      includeKey: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
      excludeKey: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
    }];
  };

  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };


  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster];
  };

  const generateTableRow = (item: RedisModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    srcCluster: item.master_domain,
    srcClusterId: item.id,
    targetClusterId: 0,
    targetBusines: 0,
    targetCluster: '',
    includeKey: ['*'],
    excludeKey: [],
  });

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
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
  const handleChangeCluster = async (index: number, domain: string) => {
    const ret = await listClusterList(currentBizId, { domain });
    if (ret.length < 1) {
      return;
    }
    const data = ret[0];
    const row = generateTableRow(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
  };

  defineExpose<Exposes>({
    getValue: () => Promise.all<CrossBusinessInfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<CrossBusinessInfoItem>
    }) => item.getValue())),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
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
