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
    field="cluster.cluster_domains"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="300"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <Textarea
      v-model="modelValue.cluster_domains"
      :placeholder="t('请输入集群域名_多个集群用分隔符输入')"
      @change="handleInputChange" />
  </Column>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selected"
    @change="handleSelectorChange" />
</template>
<script lang="ts">
  const domainIdMap: Record<string, number> = {};
</script>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import { Column, Textarea } from '@components/editable-table/Index.vue';

  interface Props {
    selectedIds: number[];
  }

  interface Emits {
    (e: 'batch-edit', list: TendbhaModel[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cluster_ids: number[];
    cluster_domains: string;
  }>({
    default: () => [],
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selected = computed<Record<string, TendbhaModel[]>>(() => ({
    [ClusterTypes.TENDBHA]: props.selectedIds.map(
      (id) =>
        ({
          id,
          master_domain: domainIdMap[id],
        }) as unknown as TendbhaModel,
    ),
  }));

  let notFounds: string[];
  const rules = [
    {
      validator: (value: string) => value.split(batchSplitRegex).every((item) => domainRegex.test(item)),
      message: t('集群域名格式不正确'),
      trigger: 'change',
    },
    {
      validator: (value: string) => {
        notFounds = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!domainIdMap[item]) {
            notFounds.push(item);
          }
        });
        return !notFounds.length;
      },
      message: () => t('目标集群xx不存在', [notFounds.join(',')]),
      trigger: 'blur',
    },
  ];

  const { run: queryCluster, loading } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.cluster_ids = [];
      if (data.length) {
        Object.assign(domainIdMap, Object.fromEntries(data.map((cur) => [cur.master_domain, cur.id])));
        modelValue.value.cluster_ids = data.map((item) => item.id);
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    queryCluster({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      exact_domain: value.split(batchSplitRegex).join(','),
    });
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    const dataList = selected[ClusterTypes.TENDBHA];
    Object.assign(domainIdMap, Object.fromEntries(dataList.map((cur) => [cur.master_domain, cur.id])));
    emits('batch-edit', dataList);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
