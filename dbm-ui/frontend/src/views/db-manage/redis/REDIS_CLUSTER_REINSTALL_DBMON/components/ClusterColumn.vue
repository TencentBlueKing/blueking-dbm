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
    :min-width="150"
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
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    :cluster-types="[ClusterTypes.REDIS, ClusterTypes.REDIS_INSTANCE]"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import type RedisModel from '@services/model/redis/redis';
  import { getGlobalCluster } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';
  import { getRedisList } from '@services/source/redis';
  import ClusterSelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  export type IValue = RedisModel;

  interface Props {
    selected: Array<typeof modelValue.value>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    id: number;
    master_domain: string;
    cluster_type: string;
  }>({
    required: true,
  });

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      id: ClusterTypes.REDIS,
      name: t('Redis 集群'),
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
          ].join(','),
          ...params,
        }),
      multiple: false,
    },
    [ClusterTypes.REDIS_INSTANCE]: {
      id: ClusterTypes.REDIS_INSTANCE,
      name: t('Redis 主从'),
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: ClusterTypes.REDIS_INSTANCE,
          ...params,
        }),
      multiple: false,
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const showSelector = ref(false);
  const selectedClusters = computed(() => ({
    [ClusterTypes.REDIS]: props.selected.filter((item) =>
      [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ].includes(item.cluster_type as ClusterTypes),
    ) as RedisModel[],
    [ClusterTypes.REDIS_INSTANCE]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.REDIS_INSTANCE,
    ) as RedisModel[],
  }));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'blur',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
  ];

  const { loading, run: queryCluster } = useRequest(getGlobalCluster<RedisModel>, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data.results;
      if (item) {
        modelValue.value = {
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          id: item.id,
          master_domain: item.master_domain,
          cluster_type: item.cluster_type,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      id: 0,
      master_domain: value,
      cluster_type: '',
    };
  };

  const handleSelectorChange = (selected: Record<string, RedisModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.master_domain && !modelValue.value.id) {
        queryCluster({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
            ClusterTypes.REDIS_INSTANCE,
          ].join(','),
          db_type: DBTypes.REDIS,
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
