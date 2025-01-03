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
    field="cluster.domain"
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
    <div style="flex: 1">
      <Input
        v-model="modelValue.domain"
        :placeholder="t('请输入集群域名')"
        @change="handleInputChange" />
    </div>
  </Column>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import { Column, Input } from '@components/editable-table/Index.vue';

  interface Props {
    selected: {
      id: number;
      domain: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: SqlserverHaModel[]): void;
    (e: 'change', data: ServiceReturnType<typeof filterClusters>[number]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    id?: number;
    domain: string;
  }>({
    default: () => ({
      domain: '',
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, SqlserverHaModel[]>>(() => ({
    [ClusterTypes.SQLSERVER_HA]: props.selected.map(
      (item) =>
        ({
          id: item.id,
          master_domain: item.domain,
        }) as SqlserverHaModel,
    ),
  }));

  const rules = [
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('集群域名格式不正确'),
      trigger: 'change',
    },
    {
      validator: () => {
        if (!modelValue.value.domain) {
          return true;
        }
        return Boolean(modelValue.value.id);
      },
      message: t('目标集群不存在'),
      trigger: 'blur',
    },
  ];

  const { run: queryCluster, loading } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.id = undefined;
      if (data.length) {
        modelValue.value.id = data[0].id;
        emits('change', data[0]);
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, SqlserverHaModel[]>) => {
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
