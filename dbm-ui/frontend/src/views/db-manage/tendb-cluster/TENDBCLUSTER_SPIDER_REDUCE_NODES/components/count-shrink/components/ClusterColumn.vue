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
    :min-width="300"
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
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selectedClusters"
    support-offline-data
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

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

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
    id: number;
    master_count: number;
    master_domain: string;
    role: string;
    slave_count: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbClusterModel[]>>(() => ({
    [ClusterTypes.TENDBCLUSTER]: props.selected as TendbClusterModel[],
  }));

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: TendbClusterModel) => data.spider_master.length <= 2 && data.spider_slave.length <= 1,
          tip: t('Spider_Master至少保留2台_Spider_Slave至少保留1台'),
        },
      ],
    },
  } as Record<ClusterTypes, TabConfig>;

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
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        if (modelValue.value.master_count > 2 || modelValue.value.slave_count > 1) {
          return true;
        }
        if (modelValue.value.master_count <= 2) {
          return t('Spider_Master至少保留2台');
        }
        if (modelValue.value.slave_count <= 1) {
          return t('Spider_Slave至少保留1台');
        }
        return true;
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbClusterModel>, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          id: item.id,
          master_count: item.spider_master.length,
          master_domain: item.master_domain,
          role: item.spider_slave.length ? 'spider_slave' : 'spider_master',
          slave_count: item.spider_slave.length,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      id: 0,
      master_count: 0,
      master_domain: value,
      role: '',
      slave_count: 0,
    };
  };

  const handleSelectorChange = (selected: Record<string, TendbClusterModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBCLUSTER]);
  };

  watch(
    modelValue,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
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
