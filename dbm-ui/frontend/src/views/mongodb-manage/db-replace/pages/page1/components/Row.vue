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
        :data="data.ip"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.role"
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
        :placeholder="t('选择主机后自动生成')" />
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

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderHost from '@views/mongodb-manage/components/edit-field/HostName.vue';
  import type { SpecInfo } from '@views/mongodb-manage/components/edit-field/spec-select/components/Panel.vue';
  import type { IListItem } from '@views/mongodb-manage/components/edit-field/spec-select/components/Select.vue';
  import RenderTargetSpec from '@views/mongodb-manage/components/edit-field/spec-select/Index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string;
    clusterId: number;
    clusterType: string;
    role: string;
    machineType: string;
    cluster: {
      domain: string;
      isStart: boolean;
      isGeneral: boolean;
      rowSpan: number;
    };
    currentSpec?: SpecInfo;
    bkCloudId?: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ip: '',
    clusterId: 0,
    clusterType: '',
    machineType: '',
    role: '',
    cluster: {
      domain: '',
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
  });
</script>
<script setup lang="ts">
  interface Props {
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

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const hostRef = ref<InstanceType<typeof RenderHost>>();
  const specRef = ref<InstanceType<typeof RenderTargetSpec>>();
  const specList = ref<IListItem[]>([]);

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
        value: item.spec_id,
        label: item.spec_name,
        specData: {
          name: item.spec_name,
          cpu: item.cpu,
          id: item.spec_id,
          mem: item.mem,
          count: 0,
          storage_spec: item.storage_spec,
        },
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
          spec_cluster_type: clusterType,
          spec_machine_type: machineType,
          limit: -1,
          offset: 0,
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
