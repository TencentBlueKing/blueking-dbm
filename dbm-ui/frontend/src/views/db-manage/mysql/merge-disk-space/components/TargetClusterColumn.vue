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
    :disabled-method="disabledMethod"
    field="target_clusters"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="200"
    required>
    <EditableInput
      v-model="localValue"
      :placeholder="t('请输入集群域名')"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          v-bk-tooltips="t('选择集群')"
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableInput>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  const modelValue = defineModel<
    {
      cluster_type: string;
      id: number;
      master_domain: string;
    }[]
  >({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.TENDBHA]: {
          multiple: false,
          showPreviewResultTitle: true,
        },
        [ClusterTypes.TENDBSINGLE]: {
          multiple: false,
          showPreviewResultTitle: true,
        },
      }) as unknown as Record<string, TabConfig>,
  );

  const localValue = ref('');
  const showSelector = ref(false);
  const selectedClusters = shallowRef<{ [key: string]: TendbhaModel[] }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });
  let formatError = '';
  let existError = '';

  const rules = [
    {
      message: t('集群域名格式不正确:xx', [formatError]),
      trigger: 'blur',
      validator: () =>
        !localValue.value ||
        localValue.value.split(batchSplitRegex).every((item) => {
          if (domainRegex.test(item)) {
            return true;
          } else {
            formatError = item;
            return false;
          }
        }),
    },
    {
      message: t('目标集群xx不存在', [existError]),
      trigger: 'blur',
      validator: () =>
        !localValue.value ||
        modelValue.value.every((item) => {
          if (item.id) {
            return true;
          } else {
            existError = item.master_domain;
            return false;
          }
        }),
    },
  ];

  const { loading, run: queryClustersRun } = useRequest(
    (params: { bk_biz_id: number; domains: string[] }) =>
      Promise.all(
        params.domains.map((domain) =>
          filterClusters<TendbhaModel>({
            bk_biz_id: params.bk_biz_id,
            exact_domain: domain,
          }),
        ),
      ).then((results) => results.flat()),
    {
      manual: true,
      onSuccess: (data) => {
        if (data.length) {
          modelValue.value = data.map((cluster) => ({
            cluster_type: cluster.cluster_type,
            id: cluster.id,
            master_domain: cluster.master_domain,
          }));
          localValue.value = data.map((item) => item.master_domain).join(',');
          selectedClusters.value = data.reduce<typeof selectedClusters.value>(
            (acc, item) => {
              Object.assign(acc, {
                [item.cluster_type]: [...acc[item.cluster_type], item],
              });
              return acc;
            },
            {
              [ClusterTypes.TENDBHA]: [],
              [ClusterTypes.TENDBSINGLE]: [],
            },
          );
        }
      },
    },
  );

  const disabledMethod = (rowData?: any) => {
    if (!rowData.source_cluster.id) {
      return t('请先选择源集群');
    }
    return '';
  };

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    if (!value) {
      return;
    }
    modelValue.value = [];
    queryClustersRun({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      domains: value.split(batchSplitRegex),
    });
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    selectedClusters.value = selected;
    modelValue.value = Object.values(selected)
      .flat()
      .map((cluster) => ({
        cluster_type: cluster.cluster_type,
        id: cluster.id,
        master_domain: cluster.master_domain,
      }));
    localValue.value = Object.values(selected)
      .flat()
      .map((item) => item.master_domain)
      .join(',');
  };

  watch(
    modelValue,
    () => {
      if (!localValue.value && modelValue.value?.[0]?.master_domain) {
        queryClustersRun({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          domains: modelValue.value.map((item) => item.master_domain),
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .select-icon {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
