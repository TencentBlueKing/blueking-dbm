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
    :loading="isLoading"
    :min-width="300"
    required
    :validate-delay="300">
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select-button"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <div style="flex: 1">
      <EditableInput
        v-model="modelValue.master_domain"
        :placeholder="t('请输入集群域名')" />
      <BkLoading
        v-if="modelValue.related_clusters?.length"
        class="related-clusters"
        :loading="relatedClusterLoading">
        {{ t('含n个同机关联集群', { n: modelValue.related_clusters.length }) }}
        <p
          v-for="item in modelValue.related_clusters"
          :key="item.id">
          -- {{ item.domain }}
        </p>
      </BkLoading>
    </div>
  </EditableColumn>
  <ClusterSelector
    :key="clusterTypes.join(',')"
    v-model:is-show="showSelector"
    :cluster-types="clusterTypes"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';
  import { getRelatedClustersByClusterIds } from '@services/source/mongodb';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    clusterTypes?: string[];
    selected: {
      cluster_type: string;
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', value: MongodbModel[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cluster_type?: string;
    id?: number;
    master_domain?: string;
    related_clusters?: {
      domain: string;
      id: number;
    }[];
  }>({
    default: () => ({
      domain: '',
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => domainRegex.test(value),
    },
    {
      message: t('目标集群不存在'),
      trigger: 'change',
      validator: () => Boolean(modelValue.value.id),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.master_domain === value).length < 2,
    },
  ];

  const selectedClusters = computed(() => ({
    [ClusterTypes.MONGO_REPLICA_SET]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.MONGO_REPLICA_SET,
    ) as MongodbModel[],
    [ClusterTypes.MONGO_SHARED_CLUSTER]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER,
    ) as MongodbModel[],
  }));

  const { loading: isLoading, run: runFilterClusters } = useRequest(filterClusters<MongodbModel>, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        [modelValue.value] = data;
      }
    },
  });

  const { loading: relatedClusterLoading, run: queryRelatedClusters } = useRequest(getRelatedClustersByClusterIds, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.related_clusters = [];
      if (data.length) {
        modelValue.value.related_clusters = data[0].related_clusters.map((item) => ({
          domain: item.master_domain,
          id: item.id,
        }));
      }
    },
  });

  watch(
    () => modelValue.value.master_domain,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
        modelValue.value.id = undefined;
        runFilterClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: modelValue.value.master_domain,
        });
      }
      if (!modelValue.value.master_domain) {
        modelValue.value.id = undefined;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => modelValue.value.id,
    (id) => {
      if (id && modelValue.value.cluster_type === ClusterTypes.MONGO_REPLICA_SET) {
        queryRelatedClusters({
          cluster_ids: [id],
        });
      } else {
        modelValue.value.related_clusters = [];
      }
    },
  );

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (selected: Record<string, MongodbModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .related-clusters {
    padding: 8px;
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
    background: #fafbfd;
  }
</style>
