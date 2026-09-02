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
  <EditableColumn
    :append-rules="rules"
    field="originProxy.ip"
    fixed="left"
    :label="t('目标Proxy主机')"
    :loading="loading"
    :min-width="200"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleChange" />
  </EditableColumn>
  <EditableColumn
    :label="t('关联集群')"
    :loading="loading"
    :min-width="200"
    readonly
    :rowspan="rowspan">
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-for="item in modelValue.related_clusters"
        :key="item.id">
        <p>
          {{ item.master_domain }}
        </p>
      </div>
    </EditableBlock>
  </EditableColumn>
  <HostSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :data-source-map="dataSourceMap"
    :tab-name-map="{ [ClusterTypes.TENDBHA]: t('Proxy 主机') }"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { checkInstance } from '@services/source/dbbase';
  import { getTendbhaMachineList } from '@services/source/tendbha';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, { type HostModel, type HostSelectorValues } from '@components/host-selector/Index.vue';

  export type SelectorItem = HostModel<ClusterTypes.TENDBHA>;

  interface Props {
    handleRowMerge: () => void;
    rowspan: number;
    selected: Array<typeof modelValue.value>;
  }

  type Emits = (e: 'batch-edit', list: SelectorItem[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    city: string;
    ip: string;
    // 合并行时使用
    merge_key: string;
    related_clusters: ServiceReturnType<typeof checkInstance>[0]['related_clusters'];
    related_instances: ServiceReturnType<typeof checkInstance>;
    role: string;
    spec_config: TendbhaModel['masters'][number]['spec_config'];
    spec_id_list: number[];
    subzones: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  // Proxy 主机：默认角色过滤改为 proxy
  const dataSourceMap = {
    [ClusterTypes.TENDBHA]: (params: ServiceParameters<typeof getTendbhaMachineList>) =>
      getTendbhaMachineList({
        ...params,
        instance_role: 'proxy',
      }),
  };

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'change',
      validator: (value: string) => !value || props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('主机不包含任何 Proxy 实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'proxy',
    },
  ];

  const showSelector = ref(false);
  const selectedInstances = computed(
    () =>
      ({
        [ClusterTypes.TENDBHA]: props.selected,
      }) as unknown as HostSelectorValues<ClusterTypes.TENDBHA>,
  );

  const { loading, run: queryInstance } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const relatedInstances = data;
        const [hostInfo] = data;
        const relatedClusters = _.sortBy(hostInfo.related_clusters, 'id');
        const [{ region, zone_names: zoneNames }] = relatedClusters;
        modelValue.value = {
          bk_cloud_id: hostInfo.bk_cloud_id,
          bk_host_id: hostInfo.bk_host_id,
          city: region && region !== 'default' ? region : '',
          ip: hostInfo.ip,
          merge_key: relatedClusters.map((i) => i.id).join(','),
          related_clusters: relatedClusters,
          related_instances: relatedInstances,
          role: hostInfo.role,
          spec_config: hostInfo.spec_config,
          spec_id_list: relatedInstances.map((item) => item.spec_config.id),
          subzones: zoneNames?.join(',') || '',
        };
        setTimeout(() => {
          props.handleRowMerge();
        });
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = Object.assign(
      {},
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        city: '',
        ip: value,
        merge_key: '',
        related_clusters: [],
        related_instances: [],
        role: '',
        spec_config: {} as TendbhaModel['masters'][number]['spec_config'],
        spec_id_list: [],
        subzones: '',
      },
    );
  };

  const handleSelectorChange = (selected: HostSelectorValues<ClusterTypes.TENDBHA>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryInstance({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA],
          db_type: DBTypes.MYSQL,
          instance_addresses: [modelValue.value.ip],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
