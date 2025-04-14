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
    field="host.ip"
    fixed="left"
    :label="t('待替换的主机')"
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
      @change="handleInputChange" />
  </EditableColumn>
  <InstanceSelector
    :key="clusterType"
    v-model:is-show="showSelector"
    :cluster-types="['mongoCluster']"
    :selected="selectedIps"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { getMongoInstancesList, getMongoTopoList } from '@services/source/mongodb';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    clusterType: ClusterTypes;
    selected: {
      ip: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: MongodbInstanceModel[]): void;
    (e: 'append-row'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id?: number;
    cluster_id: number;
    cluster_type: MongodbInstanceModel['cluster_type'];
    ip: string;
    machine_type: MongodbInstanceModel['machine_type'];
    master_domain: string;
    related_clusters: {
      id: number;
      master_domain: string;
    }[];
    shard: string;
    spec_config: MongodbInstanceModel['spec_config'];
  }>({
    default: () => ({
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      cluster_type: ClusterTypes.MONGO_REPLICA_SET as MongodbInstanceModel['cluster_type'],
      ip: '',
      machine_type: '' as MongodbInstanceModel['machine_type'],
      master_domain: '',
      related_clusters: [],
      shard: '',
      spec_config: {} as MongodbInstanceModel['spec_config'],
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const tabListConfig = computed(
    () =>
      ({
        mongoCluster: [
          {
            name: t('待替换的主机'),
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getMongoInstancesList>) =>
                getMongoInstancesList({
                  ...params,
                  cluster_type: props.clusterType,
                }),
              multiple: true,
            },
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getMongoTopoList>) =>
                getMongoTopoList({
                  ...params,
                  cluster_type: props.clusterType,
                }),
            },
          },
          {
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getMongoInstancesList>) =>
                getMongoInstancesList({
                  ...params,
                  cluster_type: props.clusterType,
                }),
            },
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getMongoTopoList>) =>
                getMongoTopoList({
                  ...params,
                  cluster_type: props.clusterType,
                }),
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );
  const selectedIps = computed<InstanceSelectorValues<IValue>>(
    () =>
      ({
        mongoCluster: props.selected,
      }) as unknown as InstanceSelectorValues<IValue>,
  );

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return Boolean(modelValue.value.bk_host_id);
      },
    },
  ];

  const { loading, run: queryHost } = useRequest(getMongoInstancesList, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data.results;
      if (item) {
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_id: item.cluster_id,
          cluster_type: item.cluster_type,
          ip: item.ip,
          machine_type: item.machine_type,
          master_domain: item.master_domain,
          related_clusters: item.related_clusters
            .map((cluster) => ({
              id: cluster.id,
              master_domain: cluster.master_domain,
            }))
            .filter((cluster) => cluster.master_domain !== item.master_domain),
          shard: item.shard,
          spec_config: item.spec_config as MongodbInstanceModel['spec_config'],
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      cluster_type: ClusterTypes.MONGO_REPLICA_SET as MongodbInstanceModel['cluster_type'],
      ip: value,
      machine_type: '' as MongodbInstanceModel['machine_type'],
      master_domain: '',
      related_clusters: [],
      shard: '',
      spec_config: {} as MongodbInstanceModel['spec_config'],
    };
    if (value) {
      queryHost({
        instance_address: value,
      });
    }
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.mongoCluster as unknown as MongodbInstanceModel[]);
  };

  watch(
    () => modelValue.value.ip,
    (value) => {
      handleInputChange(value);
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
