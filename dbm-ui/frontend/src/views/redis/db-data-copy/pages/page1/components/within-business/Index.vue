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
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :width="220">
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
        <RenderTableHeadColumn
          :min-width="130"
          :width="300">
          <span>{{ $t('目标集群') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :width="220">
          <span>{{ $t('包含Key') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :width="220">
          <span>{{ $t('排除Key') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          fixed="right"
          :min-width="90"
          :required="false"
          :width="120">
          {{ $t('操作') }}
        </RenderTableHeadColumn>
      </template>

      <template #data>
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :cluster-list="clusterList"
          :data="item"
          :inputed-clusters="inputedClusters"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </template>
    </RenderTable>
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisDSTHistoryJobModel  from '@services/model/redis/redis-dst-history-job';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes, LocalStorageKeys } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import type { SelectItem } from '@views/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';
  import type { InfoItem } from '@views/redis/db-data-copy/pages/page1/Index.vue';

  import { destroyLocalStorage } from '../../Index.vue';

  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './Row.vue';

  interface Props {
    clusterList: SelectItem[];
  }

  interface Exposes {
    getValue: () => Promise<InfoItem[]>,
    resetTable: () => void
  }

  defineProps<Props>();

  const emits = defineEmits<{
    'change-table-available': [status: boolean]
  }>();

  const { t } = useI18n();

  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const rowRefs = ref();

  const selectedClusters = shallowRef<{[key: string]: Array<RedisModel>}>({ [ClusterTypes.REDIS]: [] });

  const tableAvailable = computed(() => tableData.value.findIndex(item => Boolean(item.srcCluster)) > -1);
  const inputedClusters = computed(() => tableData.value.map(item => item.srcCluster));

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      disabledRowConfig: {
        handler: (data: RedisModel) => data.redis_slave.filter(item => item.status !== 'running').length > 0,
        tip: t('slave 状态异常，无法选择'),
      },
      columnStatusFilter: (data: RedisModel) => data.redis_slave.filter(item => item.status !== 'running').length === 0,
    },
  };

  // 集群域名是否已存在表格的映射表
  let domainMemo:Record<string, boolean> = {};

  watch(() => tableAvailable.value, (status) => {
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
      targetClusterId: item.dst_cluster_id,
      includeKey: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
      excludeKey: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
    }];
    destroyLocalStorage();
  };


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
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster];
    const clustersArr = selectedClusters.value[ClusterTypes.REDIS];
    selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter(item => item.master_domain !== srcCluster);
  };

  const generateTableRow = (item: RedisModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    srcCluster: item.master_domain,
    srcClusterId: item.id,
    targetCluster: '',
    targetClusterId: 0,
    includeKey: ['*'],
    excludeKey: [],
  });

  // 批量选择
  const handelClusterChange = async (selected: Record<string, RedisModel[]>) => {
    selectedClusters.value = selected;
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
    if (!domain) {
      const { srcCluster } = tableData.value[index];
      domainMemo[srcCluster] = false;
      tableData.value[index].srcCluster = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await getRedisList({ domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length < 1) {
      return;
    }
    const data = result.results[0];
    const row = generateTableRow(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.REDIS].push(data);
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };

  defineExpose<Exposes>({
    getValue: () => Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue())),
    resetTable: () => {
      tableData.value = [createRowData()];
      selectedClusters.value[ClusterTypes.REDIS] = [];
      domainMemo = {};
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
