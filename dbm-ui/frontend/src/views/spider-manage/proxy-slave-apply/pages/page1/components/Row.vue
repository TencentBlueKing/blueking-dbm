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
    <td style="padding: 0;">
      <RenderTargetCluster
        :data="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderSpec
        ref="sepcRef"
        :data="data.spec"
        :is-loading="data.isLoading"
        :select-list="specList" />
    </td>
    <td
      style="padding: 0;">
      <RenderTargetNumber
        ref="numRef"
        :data="data.targetNum"
        :is-loading="data.isLoading"
        :min="data.spec?.count" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderTargetCluster from '@views/spider-manage/common/edit-field/ClusterName.vue';

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
    clusterType: string,
    cloudId: number,
    bizId: number,
    spec?: SpecInfo;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    resource_spec: {
      spider_slave_ip_list: {
        spec_id: 1,
        count: 2
      } & SpecInfo
    }
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    clusterType: '',
    cloudId: 0,
    bizId: 0,
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'onClusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sepcRef = ref();
  const numRef = ref();

  const specList = ref<IListItem[]>([]);

  watch(() => props.data, (data) => {
    if (data?.clusterType) {
      const type = data.clusterType;
      setTimeout(() => querySpecList(type));
    }
  }, {
    immediate: true,
  });

  // 查询集群对应的规格列表
  const querySpecList = async (type: string) => {
    const ret = await getResourceSpecList({
      spec_cluster_type: type,
      limit: -1,
      offset: 0,
    });
    const retArr = ret.results;
    const res  = await getSpecResourceCount({
      bk_biz_id: Number(props.data.bizId),
      bk_cloud_id: Number(props.data.cloudId),
      spec_ids: retArr.map(item => item.spec_id),
    });
    specList.value = retArr.map(item => ({
      id: item.spec_id,
      name: item.spec_name,
      specData: {
        name: item.spec_name,
        cpu: item.cpu,
        id: item.spec_id,
        mem: item.mem,
        count: res[item.spec_id],
        storage_spec: item.storage_spec,
      },
    }));
  };


  const handleInputFinish = (value: string) => {
    emits('onClusterInputFinish', value);
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

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all([sepcRef.value.getValue(), numRef.value.getValue()]).then((data) => {
        const [specId, targetNum] = data;
        return {
          cluster_id: props.data.clusterId,
          resource_spec: {
            spider_slave_ip_list: {
              ...props.data.spec,
              ...targetNum,
              ...specId,
            },
          },
        };
      });
    },
  });

</script>
