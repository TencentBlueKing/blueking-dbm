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
    :label="label || t('目标集群')"
    :loading="isLoading"
    :min-width="300"
    required
    :validate-delay="300">
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
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
          -- {{ item.master_domain }}
        </p>
      </BkLoading>
    </div>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';
  import { findRelatedClustersByClusterIds } from '@services/source/redisToolbox';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    label?: string;
    selected: {
      cluster_type: string;
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', value: RedisModel[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cluster_type?: string;
    id?: number;
    master_domain?: string;
    related_clusters?: {
      id: number;
      master_domain: string;
    }[];
  }>({
    default: () => ({
      master_domain: '',
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const isLoading = ref(false);

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => domainRegex.test(value),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
  ];

  const selectedClusters = computed(() => ({
    [ClusterTypes.REDIS]: props.selected as RedisModel[],
  }));

  const { loading: relatedClusterLoading, run: queryRelatedClusters } = useRequest(findRelatedClustersByClusterIds, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.related_clusters = [];
      if (data.length) {
        modelValue.value.related_clusters = data[0].related_clusters;
      }
    },
  });

  watch(
    () => modelValue.value.master_domain,
    () => {
      modelValue.value.id = undefined;
      if (!modelValue.value.id && modelValue.value.master_domain) {
        isLoading.value = true;
        filterClusters<RedisModel>({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: modelValue.value.master_domain,
        })
          .then((data) => {
            if (data.length > 0) {
              [modelValue.value] = data;
            }
          })
          .finally(() => {
            isLoading.value = false;
            // editableTableColumnRef.value!.validate();
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
    () => {
      if (modelValue.value.id) {
        queryRelatedClusters({
          cluster_ids: [modelValue.value.id],
        });
      } else {
        modelValue.value.related_clusters = [];
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (selected: Record<string, RedisModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>

<style lang="less" scoped>
  .batch-host-select {
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
