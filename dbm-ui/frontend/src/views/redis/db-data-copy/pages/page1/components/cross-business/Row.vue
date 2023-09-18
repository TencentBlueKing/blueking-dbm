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
      <RenderSourceCluster
        ref="sourceClusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @on-input-finish="handleInputFinish" />
    </td>
    <td
      style="padding: 0;">
      <RenderTargetBusiness
        ref="targetBusinessRef"
        :data="data.targetBusines"
        :is-loading="data.isLoading"
        @change="handleBusinessChange" />
    </td>
    <td
      style="padding: 0;">
      <RenderTargetCluster
        ref="targetClusterRef"
        :data="data.targetClusterId"
        :is-loading="data.isLoading"
        :select-list="clusterList" />
    </td>
    <td style="padding: 0;">
      <RenderKeyRelated
        ref="includeKeyRef"
        :data="data.includeKey"
        required />
    </td>
    <td
      style="padding: 0;">
      <RenderKeyRelated
        ref="excludeKeyRef"
        :data="data.excludeKey"
        :required="false" />
    </td>
    <td :class="{'shadow-column': isFixed}">
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

  import RenderSourceCluster from '@views/redis/common/edit-field/ClusterName.vue';
  import RenderKeyRelated from '@views/redis/common/edit-field/RegexKeys.vue';
  import RenderTargetCluster,
    { type SelectItem } from '@views/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';
  import type { CrossBusinessInfoItem } from '@views/redis/db-data-copy/pages/page1/Index.vue';

  import { random } from '@utils';

  import RenderTargetBusiness from './RenderTargetBusiness.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    srcClusterId: number;
    targetClusterId: number;
    includeKey: string[];
    excludeKey: string[];
    targetBusines?: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    srcClusterId: 0,
    targetClusterId: 0,
    includeKey: ['*'],
    excludeKey: [],
  });

</script>
<script setup lang="ts">
  import { listClusterList } from '@services/redis/toolbox';

  interface Props {
    data: IDataRow,
    removeable: boolean,
    inputedClusters?: string[],
    isFixed?: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<CrossBusinessInfoItem>
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => ([]),
    isFixed: false,
  });

  const emits = defineEmits<Emits>();

  const sourceClusterRef = ref();
  const targetBusinessRef = ref();
  const targetClusterRef = ref();
  const includeKeyRef = ref();
  const excludeKeyRef = ref();
  const clusterList = ref<SelectItem[]>([]);

  // 目标业务变动后，集群列表更新
  const handleBusinessChange = async (bizId: number) => {
    const ret = await listClusterList(bizId);
    clusterList.value = ret.reduce((results, item) => {
      if (item.master_domain !== props.data.srcCluster) {
        const obj = {
          value: item.id,
          label: item.master_domain,
        };
        results.push(obj);
      }
      return results;
    }, [] as SelectItem[]);
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
      await sourceClusterRef.value.getValue();
      return await Promise.all([
        props.data.srcClusterId,
        targetBusinessRef.value.getValue(),
        targetClusterRef.value.getValue(),
        includeKeyRef.value.getValue(),
        excludeKeyRef.value.getValue(),
      ]).then((data) => {
        const [
          srcClusterId,
          targetBusines,
          targetClusterId,
          includeKey,
          excludeKey,
        ] = data;
        return {
          src_cluster: srcClusterId,
          dst_cluster: targetClusterId,
          dst_bk_biz_id: targetBusines,
          key_white_regex: includeKey.join('\n'),
          key_black_regex: excludeKey.join('\n'),
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
