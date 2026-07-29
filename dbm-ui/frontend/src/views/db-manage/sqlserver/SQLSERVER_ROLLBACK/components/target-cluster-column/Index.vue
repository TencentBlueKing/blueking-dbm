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
    field="targetCluster.master_domain"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="200"
    required>
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableInput>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import { Column as EditableColumn, Input as EditableInput } from '@components/editable-table/Index.vue';

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    cluster_type: string;
    id: number;
    master_domain: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_HA]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerHaModel) => data.id === props.cluster.id,
          tip: t('不能选择源集群'),
        },
      ],
      multiple: false,
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerSingleModel) => data.id === props.cluster.id,
          tip: t('不能选择源集群'),
        },
      ],
      multiple: false,
    },
  } as unknown as Record<string, TabConfig>;

  const showSelector = ref(false);
  const selectedClusters = shallowRef<{ [key: string]: SqlServerHaModel[] }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('不能选择源集群'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.id !== props.cluster.id,
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      const [currentCluster] = data;
      if (currentCluster) {
        modelValue.value = currentCluster;
      }
    },
  });

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'targetCluster.master_domain' && !rowData.cluster.id) {
      return t('请先选择源集群');
    }
    return '';
  };

  const handleShowSelector = () => {
    selectedClusters.value = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
    };
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      cluster_type: '',
      id: 0,
      master_domain: value,
    };
  };

  const handleSelectorChange = (selected: Record<string, SqlServerHaModel[]>) => {
    selectedClusters.value = selected;
    const [currentCluster] = [...selected[ClusterTypes.SQLSERVER_HA], ...selected[ClusterTypes.SQLSERVER_SINGLE]];
    if (currentCluster) {
      modelValue.value = currentCluster;
    }
  };

  watch(
    modelValue,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE].join(','),
          db_type: DBTypes.SQLSERVER,
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
