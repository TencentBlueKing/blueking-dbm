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
      :placeholder="t('请输入集群域名')" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="selectedClusters"
    support-offline-data
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: RedisModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cluster_type_name: string;
    id?: number;
    master_domain: string;
    proxyCount: number;
  }>({
    default: () => ({
      cluster_type_name: '',
      id: undefined,
      master_domain: '',
      proxyCount: 0,
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, RedisModel[]>>(() => ({
    [ClusterTypes.REDIS]: props.selected as RedisModel[],
  }));

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      disabledRowConfig: [
        {
          handler: (data: RedisModel) => data.proxy.length <= 2,
          tip: t('数量不足，Proxy至少保留 2 台'),
        },
      ],
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
    },
  } as unknown as Record<string, TabConfig>;

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
    {
      message: t('数量不足，Proxy至少保留 2 台'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return modelValue.value.proxyCount >= 2;
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<RedisModel>, {
    manual: true,
    onSuccess: (data) => {
      const [find] = data;
      if (find) {
        const item = new RedisModel(find);
        modelValue.value = {
          cluster_type_name: item.cluster_type_name,
          id: item.id,
          master_domain: item.master_domain,
          proxyCount: item.proxyCount || item.proxy.length,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (selected: Record<string, RedisModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.REDIS]);
  };

  watch(
    () => modelValue.value.master_domain,
    (value) => {
      modelValue.value = {
        ...modelValue.value,
        id: undefined,
        master_domain: value,
      };
      if (value) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: value,
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
