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
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleInputChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="selectedClusters"
    support-offline-data
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: RedisModel[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<
    Pick<
      RedisModel,
      | 'master_domain'
      | 'cluster_type'
      | 'cluster_type_name'
      | 'bk_cloud_id'
      | 'major_version'
      | 'cluster_capacity'
      | 'disaster_tolerance_level'
    > & {
      cluster_stats?: RedisModel['cluster_stats'];
      cluster_spec?: RedisModel['cluster_spec'];
      group_num: RedisModel['machine_pair_cnt'];
      shard_num: RedisModel['cluster_shard_num'];
      id?: number;
    }
  >({
    default: () => ({
      master_domain: '',
      cluster_type: '',
      cluster_type_name: '',
      major_version: '',
      shard_num: 0,
      group_num: 0,
      bk_cloud_id: 0,
      cluster_capacity: 0,
      disaster_tolerance_level: 'CROS_SUBZONE',
      id: undefined,
      cluster_stats: {},
      cluster_spec: {},
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, RedisModel[]>>(() => ({
    [ClusterTypes.REDIS]: props.selected.map(
      (currentCluster) =>
        ({
          id: currentCluster.id,
          master_domain: currentCluster.master_domain,
        }) as RedisModel,
    ),
  }));

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
    },
  } as unknown as Record<string, TabConfig>;

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

  const { run: queryCluster, loading } = useRequest(filterClusters<RedisModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [currentCluster] = data;
        modelValue.value = {
          id: currentCluster.id,
          master_domain: currentCluster.master_domain,
          cluster_type: currentCluster.cluster_type,
          cluster_type_name: currentCluster.cluster_type_name,
          cluster_stats: currentCluster.cluster_stats,
          cluster_spec: currentCluster.cluster_spec,
          cluster_capacity: currentCluster.cluster_capacity,
          group_num: currentCluster.machine_pair_cnt,
          shard_num: currentCluster.cluster_shard_num,
          bk_cloud_id: currentCluster.bk_cloud_id,
          major_version: currentCluster.major_version,
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
      master_domain: value,
      cluster_type: '',
      cluster_type_name: '',
      major_version: '',
      shard_num: 0,
      group_num: 0,
      bk_cloud_id: 0,
      cluster_capacity: 0,
      disaster_tolerance_level: 'CROS_SUBZONE',
      id: undefined,
      cluster_stats: {} as RedisModel['cluster_stats'],
      cluster_spec: {} as RedisModel['cluster_spec'],
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, RedisModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.REDIS]);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
