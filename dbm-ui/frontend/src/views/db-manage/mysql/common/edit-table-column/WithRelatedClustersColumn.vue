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
    <div
      :class="{
        'has-related-clusters': modelValue.related_clusters.length > 0,
      }"
      style="flex: 1">
      <EditableInput
        v-model="modelValue.master_domain"
        :placeholder="t('请输入集群域名')" />
      <div
        v-if="modelValue.related_clusters.length > 0"
        class="related-clusters">
        {{ t('含n个同机关联集群', { n: modelValue.related_clusters.length }) }}
        <p
          v-for="item in modelValue.related_clusters"
          :key="item.id">
          -- {{ item.master_domain }}
        </p>
      </div>
    </div>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';
  import { findRelatedClustersByClusterIds } from '@services/source/mysqlCluster';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    /**
     * 在添加proxy，proxy升级的场景，多加一个请求参数role: proxy  表示以proxy维度查询关联集群
     */
    role?: 'proxy';
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: TendbhaModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    id?: number;
    master_domain: string;
    related_clusters: {
      id: number;
      master_domain: string;
    }[];
  }>({
    default: () => ({
      id: undefined,
      master_domain: '',
      related_clusters: [],
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbhaModel[]>>(() => ({
    [ClusterTypes.TENDBHA]: props.selected as TendbhaModel[],
  }));

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

  const { loading, run: queryRelatedClusters } = useRequest(findRelatedClustersByClusterIds, {
    manual: true,
    onSuccess: (data) => {
      const [currentCluster] = data;
      if (currentCluster) {
        modelValue.value.related_clusters = currentCluster.related_clusters.map((item) => ({
          id: item.id,
          master_domain: item.master_domain,
        }));
      }
    },
  });

  const { run: queryCluster } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      const [currentCluster] = data;
      if (currentCluster?.id) {
        modelValue.value.id = currentCluster.id;
        queryRelatedClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: [currentCluster.id],
          role: props.role,
        });
      }
    },
  });

  watch(
    () => modelValue.value.master_domain,
    (value) => {
      if (value) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: value,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
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

  :deep(.has-related-clusters .bk-editable-table-column-error) {
    top: 21.5%;
  }
</style>
