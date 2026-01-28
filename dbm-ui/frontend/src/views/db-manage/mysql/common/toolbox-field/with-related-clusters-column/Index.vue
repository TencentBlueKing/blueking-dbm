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
    required
    :validate-delay="300"
    :width="350">
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
        v-model.trim="modelValue.master_domain"
        :placeholder="t('请输入集群域名')"
        @change="handleChange" />
      <BkLoading
        v-if="modelValue.related_clusters.length > 0"
        class="related-clusters"
        :loading="relatedLoading">
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
    v-model="selectedClusters"
    v-model:is-show="showSelector"
    add-related-cluster
    :cluster-types="localClusterTypes"
    :related-cluster-data-source-map="relatedClusterDataSourceMap"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';
  import { findRelatedClustersByClusterIds } from '@services/source/mysqlCluster';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  interface ClusterBase {
    cluster_type?: ClusterTypes;
    id: number;
    master_domain: string;
  }

  type WithRelatedClusterItem = {
    related_clusters: ClusterBase[];
    spec_id_list?: number[];
  } & ClusterBase &
    Partial<TendbhaModel>;

  interface Props {
    /**
     * 是否允许重复
     */
    allowRepeat?: boolean;
    /**
     * 选择器tab集群类型，不传默认 TENDBHA
     */
    clusterTypes?: (ClusterTypes.TENDBHA | ClusterTypes.TENDBSINGLE)[];
    /**
     * @example proxy升级的场景，多加一个请求参数role: proxy  表示以proxy维度查询关联集群
     * @example 单节点升级的场景，多加一个请求参数role: orphan  表示以orphan维度查询关联集群
     */
    role?: 'proxy' | 'orphan';
    selected: WithRelatedClusterItem[];
  }

  interface Emits {
    (e: 'batch-edit', list: any[]): void;
    (e: 'request-success'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<WithRelatedClusterItem>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const localClusterTypes = computed<NonNullable<Props['clusterTypes']>>(() => {
    if (props.clusterTypes) {
      return props.clusterTypes;
    }
    return [ClusterTypes.TENDBHA];
  });

  const clusterMap = computed(() => {
    return props.selected.reduce<Record<string, ClusterBase>>((acc, cluster) => {
      Object.assign(acc, {
        [cluster.master_domain]: cluster,
      });
      cluster.related_clusters.forEach((item) => {
        Object.assign(acc, {
          [item.master_domain]: cluster, // 关联集群映射到所属集群
        });
      });
      return acc;
    }, {});
  });

  const selectedClusters = computed(() => {
    const clusterMemo = new Set<string>();
    const result = {
      [ClusterTypes.TENDBHA]: [] as TendbhaModel[],
      [ClusterTypes.TENDBSINGLE]: [] as TendbhaModel[],
    };

    const addCluster = (cluster: TendbhaModel) => {
      if (!clusterMemo.has(cluster.master_domain)) {
        const targetList =
          cluster.cluster_type === ClusterTypes.TENDBHA
            ? result[ClusterTypes.TENDBHA]
            : result[ClusterTypes.TENDBSINGLE];
        targetList.push(cluster);
        clusterMemo.add(cluster.master_domain);
      }
    };

    props.selected.forEach((cluster) => {
      addCluster(cluster as TendbhaModel);
      cluster.related_clusters.forEach((item) => {
        addCluster(item as TendbhaModel);
      });
    });

    return result;
  });

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) =>
        props.allowRepeat || !value || props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        const target = clusterMap.value[value].master_domain;
        if (target && target !== value) {
          return t('目标集群是集群target的关联集群_请勿重复添加', { target });
        }
        return true;
      },
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
  ];

  const { loading: relatedLoading, run: queryRelatedClusters } = useRequest(findRelatedClustersByClusterIds, {
    manual: true,
    onSuccess: (data) => {
      const [currentCluster] = data;
      if (currentCluster) {
        modelValue.value.related_clusters = currentCluster.related_clusters;
      }
    },
  });

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbhaModel>, {
    manual: true,
    onSuccess: (data) => {
      const [currentCluster] = data;
      if (currentCluster?.id) {
        const roleListKey = props.role === 'proxy' ? 'proxies' : 'masters';
        modelValue.value = Object.assign({}, new TendbhaModel(currentCluster), {
          related_clusters: [],
          spec_id_list: ((currentCluster[roleListKey] as TendbhaModel['masters']) || [])
            .map((item) => item.spec_config.id)
            .filter((specId) => Boolean(specId)),
        });
        emits('request-success');

        queryRelatedClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: [currentCluster.id],
          role: currentCluster.cluster_type === ClusterTypes.TENDBSINGLE ? 'orphan' : props.role,
        });
      }
    },
  });

  const relatedClusterDataSourceMap = {
    [ClusterTypes.TENDBHA]: (params: ServiceParameters<typeof findRelatedClustersByClusterIds>) =>
      findRelatedClustersByClusterIds({ ...params, role: props.role }),
    [ClusterTypes.TENDBSINGLE]: (params: ServiceParameters<typeof findRelatedClustersByClusterIds>) =>
      findRelatedClustersByClusterIds({ ...params, role: 'orphan' }),
  };

  const handleChange = (value: string) => {
    modelValue.value = Object.assign({} as TendbhaModel, {
      cluster_type: props.clusterTypes?.[0] || ClusterTypes.TENDBHA,
      id: 0, // 重置ID，表示需要重新查询集群
      master_domain: value,
      related_clusters: [],
      spec_id_list: [],
    });
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.master_domain && !modelValue.value.id) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE].join(','),
          db_type: DBTypes.MYSQL,
          exact_domain: modelValue.value.master_domain,
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
    const dataList = localClusterTypes.value.map((type) => selected[type] || []).flat() || [];
    emits('batch-edit', dataList);
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
  }

  :deep(.has-related-clusters .bk-editable-table-column-error) {
    top: 21.5%;
  }
</style>
