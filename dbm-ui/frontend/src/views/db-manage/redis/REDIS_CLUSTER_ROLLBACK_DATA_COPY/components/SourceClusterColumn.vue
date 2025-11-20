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
    field="cluster.temp_cluster_proxy"
    fixed="left"
    :label="t('构造产物访问入口')"
    :loading="isLoading"
    required
    :width="350">
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowClusterSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditableInput
      v-model="modelValue.temp_cluster_proxy"
      :placeholder="t('请输入单个(IP 或 域名):Port')" />
    <VisitEntrySelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisRollbackModel from '@services/model/redis/redis-rollback';
  import { getRollbackList } from '@services/source/redisRollback';

  import { ClusterTypes } from '@common/const';
  import { domainPort, ipPort } from '@common/regex';

  import VisitEntrySelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      temp_cluster_proxy: string;
    }[];
  }

  type Emits = (e: 'batch-edit', value: RedisRollbackModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<RedisRollbackModel>>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      customColums: [
        {
          field: 'temp_cluster_proxy',
          label: t('构造产物访问入口'),
          showOverflowTooltip: true,
        },
        {
          field: 'prod_cluster',
          label: t('目标集群'),
          minWidth: 100,
          showOverflowTooltip: true,
        },
        {
          field: 'recovery_time_point',
          label: t('构造到指定时间'),
          showOverflowTooltip: true,
        },
      ],
      getResourceList: getRollbackList,
      previewResultKey: 'temp_cluster_proxy',
      searchSelectList: [
        {
          id: 'temp_cluster_proxy',
          name: t('访问入口'),
        },
        {
          id: 'prod_cluster',
          name: t('目标集群'),
        },
      ],
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const rules = [
    {
      message: t('访问入口不能为空'),
      trigger: 'change',
      validator: (value: string) => Boolean(value),
    },
    {
      message: t('访问入口格式不正确'),
      trigger: 'change',
      validator: (value: string) => ipPort.test(value) || domainPort.test(value),
    },
    {
      message: t('访问入口不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
    {
      message: t('目标访问入口重复'),
      trigger: 'change',
      validator: (value: string) => props.selected.filter((item) => item.temp_cluster_proxy === value).length < 2,
    },
  ];

  const isShowClusterSelector = ref(false);
  const isLoading = ref(false);

  const selectedClusters = computed<Record<string, RedisRollbackModel[]>>(() => ({
    [ClusterTypes.REDIS]: props.selected.map(
      (currentCluster) =>
        ({
          id: currentCluster.id,
          temp_cluster_proxy: currentCluster.temp_cluster_proxy,
        }) as RedisRollbackModel,
    ),
  }));

  watch(
    () => modelValue.value.temp_cluster_proxy,
    () => {
      modelValue.value.id = 0;
      if (!modelValue.value.id && modelValue.value.temp_cluster_proxy) {
        isLoading.value = true;
        getRollbackList({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          temp_cluster_proxy: modelValue.value.temp_cluster_proxy,
        })
          .then((data) => {
            if (data.results.length > 0) {
              [modelValue.value] = data.results;
            }
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
      if (!modelValue.value.temp_cluster_proxy) {
        modelValue.value.id = 0;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, RedisRollbackModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>
