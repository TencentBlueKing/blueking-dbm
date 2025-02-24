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
      <RenderHost
        ref="hostRef"
        :cluster-node-count="clusterNodeCount"
        :data="data.ip"
        :row-data="data"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="roleText"
        :is-loading="data.isLoading"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <!-- 跨行合并 -->
    <td
      v-if="data.cluster.isGeneral || data.cluster.isStart"
      :rowspan="data.cluster.rowSpan"
      style="padding: 0">
      <RenderText
        :data="data.cluster.domain"
        :is-loading="data.isLoading"
        :placeholder="t('选择主机后自动生成')">
        <RelatedClusters
          v-if="data.cluster.domain && data.relatedClusters.length > 0"
          :clusters="data.relatedClusters" />
      </RenderText>
    </td>
    <td style="padding: 0">
      <RenderTargetSpec
        ref="specRef"
        :data="data.currentSpec"
        :is-loading="data.isLoading"
        :select-list="specList" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import type { SpecInfo } from '@views/db-manage/mongodb/components/edit-field/spec-select/components/Panel.vue';
  import type { IListItem } from '@views/db-manage/mongodb/components/edit-field/spec-select/components/Select.vue';
  import RenderTargetSpec from '@views/db-manage/mongodb/components/edit-field/spec-select/Index.vue';
  import RelatedClusters from '@views/db-manage/mongodb/components/RelatedClusters.vue';

  import { random } from '@utils';

  import RenderHost from './HostName.vue';

  export interface IDataRow {
    bkCloudId?: number;
    cluster: {
      domain: string;
      isGeneral: boolean;
      isStart: boolean;
      rowSpan: number;
    };
    clusterId: number;
    clusterType: string;
    currentSpec?: SpecInfo;
    ip: string;
    isLoading: boolean;
    machineType: string;
    relatedClusters: string[];
    role: string;
    rowKey: string;
    shard: string;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    cluster: {
      domain: '',
      isGeneral: true,
      isStart: false,
      rowSpan: 1,
    },
    clusterId: 0,
    clusterType: '',
    ip: '',
    isLoading: false,
    machineType: '',
    relatedClusters: [],
    role: '',
    rowKey: random(),
    shard: '',
  });

  interface Props {
    clusterNodeCount: Record<number, Record<string, number[]>>;
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'hostInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<Record<string, number>>;
  }
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const hostRef = ref<InstanceType<typeof RenderHost>>();
  const specRef = ref<InstanceType<typeof RenderTargetSpec>>();
  const specList = ref<IListItem[]>([]);

  const roleText = computed(() => {
    const { clusterType, machineType, shard } = props.data;
    if (clusterType === ClusterTypes.MONGO_SHARED_CLUSTER && machineType === 'mongodb') {
      return shard;
    }
    return machineType || '';
  });

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value.forEach((item) => {
        Object.assign(item.specData, {
          count: data[item.specData.id],
        });
      });
    },
  });

  const { run: fetchResourceSpecList } = useRequest(getResourceSpecList, {
    manual: true,
    onSuccess(data) {
      specList.value = data.results.map((item) => ({
        label: item.spec_name,
        specData: {
          count: 0,
          cpu: item.cpu,
          id: item.spec_id,
          mem: item.mem,
          name: item.spec_name,
          storage_spec: item.storage_spec,
        },
        value: item.spec_id,
      }));
      fetchSpecResourceCount({
        bk_biz_id: currentBizId,
        bk_cloud_id: props.data.bkCloudId!,
        spec_ids: specList.value.map((item) => item.specData.id),
      });
    },
  });

  watch(
    () => [props.data.clusterType, props.data.machineType],
    ([clusterType, machineType]) => {
      if (clusterType && machineType) {
        fetchResourceSpecList({
          limit: -1,
          offset: 0,
          spec_cluster_type: 'mongodb',
          spec_machine_type: machineType,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    emits('hostInputFinish', value);
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
      return await Promise.all([hostRef.value!.getValue(), specRef.value!.getValue()]).then((data) => {
        const [ip, specId] = data;
        return {
          [ip]: specId,
        };
      });
    },
  });
</script>
