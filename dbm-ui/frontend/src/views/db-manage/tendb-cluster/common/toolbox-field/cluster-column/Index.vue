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
      @change="handleChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selected"
    :support-offline-data="supportOfflineData"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import { getTendbClusterList } from '@services/source/tendbcluster';

  interface Props {
    selected: Record<ClusterTypes.TENDBCLUSTER, TendbClusterModel[]>;
    tabListConfig?: Record<ClusterTypes.TENDBCLUSTER, TabConfig>;
    /**
     * @description 是否支持离线数据
     * @default false
     */
    supportOfflineData?: boolean;
    /**
     * @description 是否允许重复选择集群
     * @default false
     */
    allowsDuplicates?: boolean;
  }

  interface Emits {
    (e: 'batch-edit', list: TendbClusterModel[]): void;
  }

  interface Exposes {
    fetch: (params: ServiceParameters<typeof getTendbClusterList>) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    tabListConfig: () => ({}) as Record<ClusterTypes.TENDBCLUSTER, TabConfig>,
    supportOfflineData: false,
    allowsDuplicates: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<TendbClusterModel>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);

  const rules = [
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('集群域名格式不正确'),
      trigger: 'change',
    },
    {
      validator: (value: string) => {
        if (props.allowsDuplicates) {
          return true;
        }
        return props.selected[ClusterTypes.TENDBCLUSTER].filter((item) => item.master_domain === value).length < 2;
      },
      message: t('目标集群重复'),
      trigger: 'blur',
    },
    {
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return Boolean(modelValue.value.id);
      },
      message: t('目标集群不存在'),
      trigger: 'blur',
    },
  ];

  const { run: queryCluster, loading } = useRequest(getTendbClusterList, {
    manual: true,
    onSuccess: (data) => {
      const [cluster] = data.results;
      if (cluster) {
        modelValue.value = cluster;
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    if (value) {
      modelValue.value.id = 0;
      queryCluster({
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, TendbClusterModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBCLUSTER]);
  };

  defineExpose<Exposes>({
    fetch: queryCluster,
  });
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
