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
    field="srcCluster.master_domain"
    fixed="left"
    :label="t('源集群')"
    :loading="loading"
    :min-width="300"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleBatchSelect">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          class="host-select"
          type="host-select"
          @click="handleSingleSelect" />
      </template>
    </EditableInput>
  </EditableColumn>
  <!-- 批量选择 -->
  <ClusterSelector
    v-model:is-show="showBatchSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :selected="selectedClusters"
    @change="handleBatchSelectorChange" />
  <!-- 单元格选择 -->
  <ClusterSelector
    v-model:is-show="showSingleSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :selected="currentSelected"
    :tab-list-config="tabListConfig"
    @change="handleSingleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SqlServerHaModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cluster_type: ClusterTypes;
    id?: number;
    major_version: string;
    master_domain: string;
  }>({
    default: () => ({
      cluster_type: ClusterTypes.SQLSERVER_HA,
      id: undefined,
      major_version: '',
      master_domain: '',
    }),
  });

  const { t } = useI18n();

  const showSingleSelector = ref(false);
  const showBatchSelector = ref(false);
  const currentSelected = reactive({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const selectedClusters = computed<Record<string, SqlServerHaModel[]>>(() => ({
    [ClusterTypes.SQLSERVER_HA]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.SQLSERVER_HA,
    ) as SqlServerHaModel[],
    [ClusterTypes.SQLSERVER_SINGLE]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.SQLSERVER_SINGLE,
    ) as SqlServerHaModel[],
  }));

  const tabListConfig = computed(() => ({
    [ClusterTypes.SQLSERVER_HA]: {
      disabledRowConfig: [
        {
          handler: (data: any) => data.isOffline,
          tip: t('集群已禁用'),
        },
        {
          handler: (data: any) => props.selected.findIndex((item) => item.id === data.id) > -1,
          tip: t('集群已被其他行选择'),
        },
      ],
      id: ClusterTypes.SQLSERVER_HA,
      multiple: false,
      name: t('SqlServer 主从'),
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      disabledRowConfig: [
        {
          handler: (data: any) => data.isOffline,
          tip: t('集群已禁用'),
        },
        {
          handler: (data: any) => props.selected.findIndex((item) => item.id === data.id) > -1,
          tip: t('集群已被其他行选择'),
        },
      ],
      id: ClusterTypes.SQLSERVER_SINGLE,
      multiple: false,
      name: t('SqlServer 单节点'),
    },
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

  const { loading, run: queryCluster } = useRequest(filterClusters<SqlServerHaModel>, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          cluster_type: item.cluster_type,
          id: item.id,
          major_version: item.major_version,
          master_domain: item.master_domain,
        };
      }
    },
  });

  const handleBatchSelect = () => {
    showBatchSelector.value = true;
  };

  const handleSingleSelect = () => {
    showSingleSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      cluster_type: ClusterTypes.SQLSERVER_HA,
      id: undefined,
      major_version: '',
      master_domain: value,
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleBatchSelectorChange = (selected: Record<string, SqlServerHaModel[]>) => {
    const data = [...selected[ClusterTypes.SQLSERVER_HA], ...selected[ClusterTypes.SQLSERVER_SINGLE]];
    emits('batch-edit', data);
  };

  const handleSingleSelectorChange = (selected: Record<string, SqlServerHaModel[]>) => {
    const data = [...selected[ClusterTypes.SQLSERVER_HA], ...selected[ClusterTypes.SQLSERVER_SINGLE]];
    const [item] = data;
    if (item) {
      modelValue.value = {
        cluster_type: item.cluster_type,
        id: item.id,
        major_version: item.major_version,
        master_domain: item.master_domain,
      };
      Object.assign(currentSelected, selected);
    }
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .host-select {
    font-size: 14px;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
