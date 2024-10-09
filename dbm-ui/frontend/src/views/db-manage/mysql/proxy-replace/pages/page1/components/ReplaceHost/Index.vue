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
    <RenderDataRow
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
    :cluster-types="[TENDBHA_HOST]"
    :selected="selectedIntances"
    :tab-list-config="tabListConfig"
    @change="handelProxySelectorChange" />
</template>

<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { MySQLProxySwitchDetails } from '@services/model/ticket/details/mysql';

  import { useGlobalBizs } from '@stores';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

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

  const TENDBHA_HOST = 'TendbhaHost';
  const tabListConfig = {
    [TENDBHA_HOST]: [
      {
        id: [TENDBHA_HOST],
        name: t('目标Proxy主机'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 主机'),
            field: 'ip',
            role: 'proxy',
          },
        },
      },
      // {
      //   id: 'manualInput',
      //   name: t('手动输入'),
      //   tableConfig: {
      //     firsrColumn: {
      //       label: t('Proxy 主机'),
      //       field: 'ip',
      //       role: 'proxy',
      //     },
      //   },
      // },
    ],
  } as unknown as Record<string, PanelListType>;
  // 实例是否已存在表格的映射表
  let ipMemo: Record<string, boolean> = {};

  const isShowInstanceSelecotr = ref(false);
  const rowRefs = ref([] as InstanceType<typeof RenderDataRow>[]);

  const tableData = shallowRef<IDataRow[]>([createRowData({})]);
  const selectedIntances = shallowRef<InstanceSelectorValues<IValue>>({ [TENDBHA_HOST]: [] });

  watch(
    () => props.data,
    () => {
      if (props.data.length > 0) {
        tableData.value = props.data.map((item) =>
          createRowData({
            originProxy: item.origin_proxy,
            targetProxy: {
              cluster_id: item.cluster_ids[0],
              ...item.origin_proxy,
              instance_address: `${item.origin_proxy.ip}:${item.origin_proxy.port}`,
            },
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
    return !firstRow.originProxy.ip;
  };

  // 批量选择
  const handelProxySelectorChange = (data: InstanceSelectorValues<IValue>) => {
    selectedIntances.value = data;
    const newList = data[TENDBHA_HOST].reduce((results, item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        const row = createRowData({
          originProxy: {
            ip,
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            bk_biz_id: currentBizId,
            port: item.related_instances[0].port,
          },
          relatedInstances: item.related_instances.map((item) => ({
            cluster_id: item.cluster_id,
            instance: item.instance,
          })),
        });
        results.push(row);
        ipMemo[ip] = true;
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
    const ip = tableData.value[index].originProxy?.ip;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selectedIntances.value[TENDBHA_HOST];
      selectedIntances.value[TENDBHA_HOST] = clustersArr.filter((item) => item.ip !== ip);
    }
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    ipMemo = {};
    selectedIntances.value[TENDBHA_HOST] = [];
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
