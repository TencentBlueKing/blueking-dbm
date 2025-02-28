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
    :min-width="200"
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
    <EditableInput
      v-if="!modelValue.id || isInput"
      ref="input"
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @blur="isInput = false"
      @change="handleInputChange" />
    <EditableBlock
      v-else
      @click="handleClick">
      <p>{{ modelValue.master_domain }}</p>
      <p
        v-for="item in modelValue.related_clusters"
        :key="item.id">
        {{ item.master_domain }}
      </p>
    </EditableBlock>
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
  const inputRef = useTemplateRef('input');

  const isInput = ref(false);
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
      validator: () => {
        if (!modelValue.value.master_domain) {
          return true;
        }
        return Boolean(modelValue.value.id);
      },
    },
  ];

  const { run: queryRelatedClusters } = useRequest(findRelatedClustersByClusterIds, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.related_clusters = data[0].related_clusters.map((item) => ({
        id: item.id,
        master_domain: item.master_domain,
      }));
    },
  });

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbhaModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [currentCluster] = data;
        modelValue.value = {
          id: currentCluster.id,
          master_domain: currentCluster.master_domain,
          related_clusters: [],
        };
      }
    },
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.id) {
        queryRelatedClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: [modelValue.value.id],
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

  const handleInputChange = (value: string) => {
    modelValue.value = {
      id: undefined,
      master_domain: value,
      related_clusters: [],
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
  };

  const handleClick = () => {
    isInput.value = true;
    nextTick(() => {
      inputRef.value?.focus();
    });
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
