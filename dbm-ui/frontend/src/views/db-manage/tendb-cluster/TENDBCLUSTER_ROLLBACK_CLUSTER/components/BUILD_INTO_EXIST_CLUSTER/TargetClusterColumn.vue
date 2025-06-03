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
    field="target_cluster.master_domain"
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

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    cluster: {
      id: number;
    };
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    id?: number;
    master_domain: string;
  }>({
    default: () => ({
      id: undefined,
      master_domain: '',
    }),
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: TendbClusterModel) => data.id === props.cluster.id,
          tip: t('不能选择源集群'),
        },
      ],
      multiple: false,
    },
  } as unknown as Record<string, TabConfig>;

  const showSelector = ref(false);
  const selectedClusters = shallowRef<{ [key: string]: TendbClusterModel[] }>({
    [ClusterTypes.TENDBCLUSTER]: [],
  });

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
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return Boolean(modelValue.value.id);
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbClusterModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [currentCluster] = data;
        modelValue.value = {
          id: currentCluster.id,
          master_domain: currentCluster.master_domain,
        };
      }
    },
  });

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'target_cluster.master_domain' && !rowData.cluster.id) {
      return t('请先选择待回档集群');
    }
    return '';
  };

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      id: undefined,
      master_domain: value,
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, TendbClusterModel[]>) => {
    selectedClusters.value = selected;
    const [currentCluster] = selected[ClusterTypes.TENDBCLUSTER];
    if (currentCluster) {
      modelValue.value = {
        id: currentCluster.id,
        master_domain: currentCluster.master_domain,
      };
    }
  };
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
