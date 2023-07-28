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
        :model-value="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderNodeType
        :data="data.nodeType"
        :is-loading="data.isLoading" />
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
    <td>
      <div class="action-box">
        <div
          class="action-btn"
          @click="handleAppend">
          <DbIcon type="plus-fill" />
        </div>
        <div
          class="action-btn"
          :class="{
            disabled: removeable
          }"
          @click="handleRemove">
          <DbIcon type="minus-fill" />
        </div>
      </div>
    </td>
  </tr>
</template>
<script lang="ts">
  import { getResourceSpecList } from '@services/resourceSpec';

  import { random } from '@utils';

  import RenderNodeType from './RenderNodeType.vue';
  import RenderSpec from './RenderSpec.vue';
  import RenderTargetCluster from './RenderTargetCluster.vue';
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
    spec?: SpecInfo;
    targetNum?: string;
    clusterType?: string;
  }

  export interface MoreDataItem {
    specId: number;
    targetNum: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    bkCloudId: 0,
    nodeType: '',
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
    (e: 'clusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<MoreDataItem>
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
    });
    const retArr = ret.results;
    specList.value = retArr.map(item => ({
      id: item.spec_id,
      name: item.spec_name,
      specData: {
        name: item.spec_name,
        cpu: item.cpu,
        id: item.spec_id,
        mem: item.mem,
        count: 0,
        storage_spec: item.storage_spec,
      },
    }));
  };


  const handleInputFinish = (value: string) => {
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

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all([sepcRef.value.getValue(), numRef.value.getValue()]).then((data) => {
        const [specId, targetNum] = data;
        return {
          specId,
          targetNum,
        };
      });
    },
  });

</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
