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
      <RenderSourceCluster
        ref="sourceClusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.srcClusterTypeName"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderTargetBusiness
        ref="targetBusinessRef"
        :data="data.targetBusines"
        :is-loading="data.isLoading"
        @change="handleBusinessChange" />
    </td>
    <td style="padding: 0">
      <RenderTargetCluster
        ref="targetClusterRef"
        :data="data.targetClusterId"
        :is-loading="data.isLoading"
        :select-list="clusterList" />
    </td>
    <td style="padding: 0">
      <RenderKeyRelated
        ref="includeKeyRef"
        :data="data.includeKey"
        required />
    </td>
    <td style="padding: 0">
      <RenderKeyRelated
        ref="excludeKeyRef"
        :data="data.excludeKey"
        :required="false" />
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

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderSourceCluster from '@views/db-manage/redis/common/edit-field/ClusterName.vue';
  import RenderKeyRelated from '@views/db-manage/redis/common/edit-field/RegexKeys.vue';
  import RenderTargetCluster, {
    type SelectItem,
  } from '@views/db-manage/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';
  import type { CrossBusinessInfoItem } from '@views/db-manage/redis/db-data-copy/pages/page1/Index.vue';

  import { random } from '@utils';

  import RenderTargetBusiness from './RenderTargetBusiness.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    srcClusterTypeName: string;
    srcClusterId: number;
    targetClusterId: number;
    includeKey: string[];
    excludeKey: string[];
    targetBusines?: number;
  }

  export type IDataRowBatchKey = keyof Pick<IDataRow, 'includeKey' | 'excludeKey'>;

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    srcClusterTypeName: '',
    srcClusterId: 0,
    targetClusterId: 0,
    includeKey: ['*'],
    excludeKey: [],
  });
</script>
<script setup lang="ts">
  import { getRedisListByBizId } from '@services/source/redis';

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
    getValue: () => Promise<CrossBusinessInfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const sourceClusterRef = ref<InstanceType<typeof RenderSourceCluster>>();
  const targetBusinessRef = ref<InstanceType<typeof RenderTargetBusiness>>();
  const targetClusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const includeKeyRef = ref<InstanceType<typeof RenderKeyRelated>>();
  const excludeKeyRef = ref<InstanceType<typeof RenderKeyRelated>>();
  const clusterList = ref<SelectItem[]>([]);

  // 目标业务变动后，集群列表更新
  const handleBusinessChange = async (bizId: number) => {
    const result = await getRedisListByBizId({
      bk_biz_id: bizId,
      offset: 0,
      limit: -1,
    });
    clusterList.value = result.results.reduce((results, item) => {
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

  const getRowData = (): [number, Promise<string>, Promise<string>, Promise<string[]>, Promise<string[]>] => [
    props.data.srcClusterId,
    targetBusinessRef.value!.getValue(),
    targetClusterRef.value!.getValue(),
    includeKeyRef.value!.getValue(),
    excludeKeyRef.value!.getValue(),
  ];
  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [srcClusterId, targetBusines, targetClusterId, includeKey, excludeKey] = rowData.map((item) =>
        item.status === 'fulfilled' ? item.value : item.reason,
      );
      emits('clone', {
        ...props.data,
        rowKey: random(),
        targetClusterId,
        targetBusines,
        includeKey,
        excludeKey,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await sourceClusterRef.value!.getValue(true);
      return await Promise.all(getRowData()).then((data) => {
        const [srcClusterId, targetBusines, targetClusterId, includeKey, excludeKey] = data;
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
