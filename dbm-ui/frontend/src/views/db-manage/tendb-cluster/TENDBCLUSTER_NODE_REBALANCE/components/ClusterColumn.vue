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
  <Column
    :append-rules="rules"
    field="cluster.master_domain"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="150"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <Input
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleInputChange" />
  </Column>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import { Column, Input } from '@components/editable-table/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: TendbClusterModel[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<
    Pick<
      TendbClusterModel,
      | 'id'
      | 'master_domain'
      | 'bk_cloud_id'
      | 'cluster_capacity'
      | 'cluster_shard_num'
      | 'cluster_spec'
      | 'db_module_id'
      | 'machine_pair_cnt'
      | 'remote_shard_num'
      | 'disaster_tolerance_level'
    >
  >({
    default: () => ({
      id: 0,
      master_domain: '',
      bk_cloud_id: 0,
      cluster_capacity: 0,
      cluster_shard_num: 0,
      cluster_spec: {} as TendbClusterModel['cluster_spec'],
      db_module_id: 0,
      machine_pair_cnt: 0,
      remote_shard_num: 0,
      disaster_tolerance_level: 'CROS_SUBZONE',
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbClusterModel[]>>(() => ({
    [ClusterTypes.TENDBCLUSTER]: props.selected.map(
      (item) =>
        ({
          id: item.id,
          master_domain: item.master_domain,
        }) as TendbClusterModel,
    ),
  }));

  const rules = [
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('集群域名格式不正确'),
      trigger: 'change',
    },
    {
      validator: (value: string) => props.selected.filter((item) => item.master_domain === value).length < 2,
      message: t('目标集群重复'),
      trigger: 'blur',
    },
    {
      validator: () => {
        if (!modelValue.value.master_domain) {
          return true;
        }
        return Boolean(modelValue.value.id);
      },
      message: t('目标集群不存在'),
      trigger: 'blur',
    },
  ];

  const { run: queryCluster, loading } = useRequest(filterClusters<TendbClusterModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [currentCluster] = data;
        modelValue.value = {
          id: currentCluster.id,
          master_domain: currentCluster.master_domain,
          bk_cloud_id: currentCluster.bk_cloud_id,
          cluster_capacity: currentCluster.cluster_capacity,
          cluster_shard_num: currentCluster.cluster_shard_num,
          cluster_spec: currentCluster.cluster_spec,
          db_module_id: currentCluster.db_module_id,
          machine_pair_cnt: currentCluster.machine_pair_cnt,
          remote_shard_num: currentCluster.remote_shard_num,
          disaster_tolerance_level: currentCluster.disaster_tolerance_level,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      id: 0,
      master_domain: value,
      bk_cloud_id: 0,
      cluster_capacity: 0,
      cluster_shard_num: 0,
      cluster_spec: {} as TendbClusterModel['cluster_spec'],
      db_module_id: 0,
      machine_pair_cnt: 0,
      remote_shard_num: 0,
      disaster_tolerance_level: 'CROS_SUBZONE',
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, TendbClusterModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBCLUSTER]);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
