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
  <RenderData
    class="mt16"
    @batch-select-cluster="handleShowInstanceSelector">
    <RenderRow
      v-for="(item, index) in tableData"
      :key="item.rowKey"
      ref="rowRefs"
      :data="item"
      :removeable="tableData.length < 2"
      @add="(payload: IDataRow[]) => handleAppend(index, payload)"
      @remove="handleRemove(index)" />
  </RenderData>
  <InstanceSelector
    v-model:is-show="isShowInstanceSelecotr"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedIntances"
    :tab-list-config="tabListConfig"
    @change="handelProxySelectorChange" />
</template>

<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { MySQLProxySwitchDetails } from '@services/model/ticket/details/mysql';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  interface Props {
    data: MySQLProxySwitchDetails['infos'];
  }

  interface Exposes {
    getValue(): Promise<any>;
    reset(): void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        id: ClusterTypes.TENDBHA,
        name: t('目标实例'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 实例'),
            field: 'instance_address',
            role: 'proxy',
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 实例'),
            field: 'instance_address',
            role: 'proxy',
          },
        },
      },
    ],
  } as Record<ClusterTypes, PanelListType>;
  // 实例是否已存在表格的映射表
  let instanceMemo: Record<string, boolean> = {};

  const isShowInstanceSelecotr = ref(false);
  const rowRefs = ref([] as InstanceType<typeof RenderRow>[]);

  const tableData = shallowRef<IDataRow[]>([createRowData({})]);
  const selectedIntances = shallowRef<InstanceSelectorValues<IValue>>({ [ClusterTypes.TENDBHA]: [] });

  watch(
    () => props.data,
    () => {
      if (props.data.length > 0) {
        tableData.value = props.data.map((item) =>
          createRowData({
            originProxy: {
              cluster_id: item.cluster_ids[0],
              ...item.origin_proxy,
              instance_address: `${item.origin_proxy.ip}:${item.origin_proxy.port}`,
            },
            targetProxy: item.target_proxy,
          }),
        );
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowInstanceSelector = () => {
    isShowInstanceSelecotr.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.originProxy.instance_address;
  };

  // 批量选择
  const handelProxySelectorChange = (data: InstanceSelectorValues<IValue>) => {
    selectedIntances.value = data;
    const newList = data.tendbha.reduce((results, item) => {
      const instance = item.instance_address;
      if (!instanceMemo[instance]) {
        const row = createRowData({
          originProxy: {
            cluster_id: item.cluster_id,
            ip: item.ip,
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            bk_biz_id: currentBizId,
            port: item.port,
            instance_address: instance,
          },
          relatedClusters: item.related_clusters.map((item) => ({
            cluster_id: item.id,
            domain: item.master_domain,
          })),
        });
        results.push(row);
        instanceMemo[instance] = true;
      }
      return results;
    }, [] as IDataRow[]);
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
    const instanceAddress = tableData.value[index].originProxy?.instance_address;
    if (instanceAddress) {
      delete instanceMemo[instanceAddress];
      const clustersArr = selectedIntances.value[ClusterTypes.TENDBHA];
      selectedIntances.value[ClusterTypes.TENDBHA] = clustersArr.filter(
        (item) => item.instance_address !== instanceAddress,
      );
    }
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    instanceMemo = {};
    selectedIntances.value[ClusterTypes.TENDBHA] = [];
    window.changeConfirm = false;
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
    },
    reset() {
      handleReset();
    },
  });
</script>
