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
    :label="t('目标集群 (always on 集群)')"
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
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleInputChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { getLevelConfig } from '@services/source/configs';
  import { filterClusters } from '@services/source/dbbase';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SqlServerHaModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    db_module_id: number;
    id?: number;
    master_domain: string;
    system_version: string;
  }>({
    default: () => ({
      db_module_id: 0,
      id: undefined,
      master_domain: '',
      system_version: '',
    }),
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_HA]: {
      getResourceList: (params: ServiceParameters<typeof getHaClusterList>) =>
        getHaClusterList({
          ...params,
          sys_mode: 'always_on',
        }),
      id: ClusterTypes.SQLSERVER_HA,
      name: t('SqlServer 主从'),
    },
  };

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, SqlServerHaModel[]>>(() => ({
    [ClusterTypes.SQLSERVER_HA]: props.selected as SqlServerHaModel[],
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
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return Boolean(modelValue.value.id);
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      const [currentCluster] = data;
      if (currentCluster) {
        modelValue.value.id = currentCluster.id;
        modelValue.value.db_module_id = currentCluster.db_module_id;
      }
    },
  });

  const { run: getOsTypes } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.system_version =
        data.conf_items.find((item) => item.conf_name === 'system_version')?.conf_value || '';
    },
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.db_module_id) {
        getOsTypes({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          conf_type: 'deploy',
          level_name: 'module',
          level_value: modelValue.value.db_module_id,
          meta_cluster_type: ClusterTypes.SQLSERVER_HA,
          version: 'deploy_info',
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
      db_module_id: 0,
      id: undefined,
      master_domain: value,
      system_version: '',
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, SqlServerHaModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.SQLSERVER_HA]);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
