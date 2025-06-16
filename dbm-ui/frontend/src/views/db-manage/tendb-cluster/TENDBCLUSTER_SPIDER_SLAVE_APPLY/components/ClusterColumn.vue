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
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: TendbClusterModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    id: number;
    master_domain: string;
    region: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: TendbClusterModel) => data.spider_slave.length > 0,
          tip: t('该集群已有只读集群'),
        },
      ],
      id: ClusterTypes.TENDBCLUSTER,
      name: t('集群选择'),
    },
  };

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbClusterModel[]>>(() => ({
    [ClusterTypes.TENDBCLUSTER]: props.selected as TendbClusterModel[],
  }));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) => !value || props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbClusterModel>, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          id: item.id,
          master_domain: item.master_domain,
          region: item.region,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      id: 0,
      master_domain: value,
      region: '',
    };
  };

  const handleSelectorChange = (selected: Record<string, TendbClusterModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBCLUSTER]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.master_domain && !modelValue.value.id) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: ClusterTypes.TENDBCLUSTER,
          db_type: DBTypes.TENDBCLUSTER,
          exact_domain: modelValue.value.master_domain,
        });
      }
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
