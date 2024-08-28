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
    <td style="padding: 0">
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.cluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.cluster_type_name"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.nodeType"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderSpec
        ref="sepcRef"
        :data="data.rowModelData"
        :is-loading="data.isLoading"
        :select-list="specList"
        :selected-spec-id="data.selectedSpecId" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="numRef"
        :data="data.targetNum"
        :disabled="!data.cluster"
        :is-loading="data.isLoading"
        :min="data.spec?.count" />
    </td>
    <OperateColumn
      :removeable="removeable"
      show-clone
      @add="handleAppend"
      @clone="handleClone"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/db-manage/redis/common/edit-field/ClusterName.vue';

  import { random } from '@utils';

  import RenderSpec from './RenderSpec.vue';
  import RenderTargetNumber from './RenderTargetNumber.vue';
  import type { SpecInfo } from './SpecPanel.vue';
  import type { IListItem } from './SpecSelect.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    bkCloudId: number;
    nodeType: string;
    cluster_type_name: string;
    spec?: SpecInfo;
    targetNum?: string;
    clusterType?: string;
    rowModelData?: RedisModel;
    selectedSpecId?: number;
  }

  export interface MoreDataItem {
    specId: number;
    targetNum: number;
  }

  export interface InfoItem {
    cluster_id: number;
    bk_cloud_id: number;
    target_proxy_count: number;
    resource_spec: {
      proxy: {
        spec_id: number;
        count: number;
      };
    };
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    bkCloudId: 0,
    nodeType: '',
    cluster_type_name: '',
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputedClusters?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  // 查询集群对应的规格列表
  const querySpecList = async (item: RedisModel) => {
    const proxyMachineMap = {
      TwemproxyRedisInstance: 'twemproxy',
      TwemproxyTendisSSDInstance: 'twemproxy',
      PredixyTendisplusCluster: 'predixy',
      PredixyRedisCluster: 'predixy',
      RedisInstance: '',
    };
    const type = item.cluster_spec.spec_cluster_type;
    const machineType = proxyMachineMap[type];
    const specId = item.cluster_spec.spec_id;
    const specCount = item.proxy.length;
    const ret = await getResourceSpecList({
      spec_cluster_type: type,
      spec_machine_type: machineType,
      limit: -1,
      offset: 0,
    });
    const retArr = ret.results;
    const arr = retArr.map((item) => ({
      value: item.spec_id,
      label: item.spec_id === specId ? `${item.spec_name} ${t('((n))台', { n: specCount })}` : item.spec_name,
      specData: {
        name: item.spec_name,
        cpu: item.cpu,
        id: item.spec_id,
        mem: item.mem,
        count: 0,
        storage_spec: item.storage_spec,
      },
    }));
    return arr;
  };

  const { t } = useI18n();

  const specList = ref<IListItem[]>([]);
  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const sepcRef = ref<InstanceType<typeof RenderSpec>>();
  const numRef = ref<InstanceType<typeof RenderTargetNumber>>();

  watch(
    () => props.data.rowModelData,
    async (rowData) => {
      if (!rowData) {
        return;
      }
      const specListRaw = await querySpecList(rowData);
      const proxySpecList = rowData.proxy.map((proxyItem) => proxyItem.spec_config.id);
      const proxySpecSet = new Set(proxySpecList);
      specList.value = specListRaw.map((specItem) =>
        Object.assign(specItem, { isCurrent: proxySpecSet.has(specItem.specData.id) }),
      );
      getSpecResourceCount({
        bk_biz_id: rowData.bk_biz_id,
        bk_cloud_id: rowData.bk_cloud_id,
        spec_ids: specList.value.map((item) => item.specData.id),
      }).then((data) => {
        specList.value = specList.value.map((item) => ({
          ...item,
          count: data[item.specData.id],
        }));
      });
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: RedisModel) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  const getRowData = () => [sepcRef.value!.getValue(), numRef.value!.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits('clone', {
        ...props.data,
        rowKey: random(),
        isLoading: false,
        targetNum: rowInfo[1] || '',
        selectedSpecId: rowInfo[0],
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue(true);
      return await Promise.all([sepcRef.value!.getValue(), numRef.value!.getValue()]).then((data) => {
        const [specId, targetNum] = data;
        return {
          cluster_id: props.data.clusterId,
          bk_cloud_id: props.data.bkCloudId,
          target_proxy_count: targetNum,
          resource_spec: {
            proxy: {
              spec_id: specId,
              count: props.data.spec?.count ? targetNum - props.data.spec.count : targetNum,
            },
          },
        };
      });
    },
  });
</script>
