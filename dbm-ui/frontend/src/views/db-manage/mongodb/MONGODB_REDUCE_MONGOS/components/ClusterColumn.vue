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
    :label="t('目标分片集群')"
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
      @change="handleInputChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongoDBModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: MongoDBModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    id?: number;
    master_domain: string;
    mongos: MongoDBModel['mongos'];
    spec_config: MongoDBModel['mongos'][0]['spec_config'];
  }>({
    default: () => ({
      bk_cloud_id: 0,
      id: undefined,
      master_domain: '',
      mongos: [] as MongoDBModel['mongos'],
      spec_config: {} as MongoDBModel['mongos'][0]['spec_config'],
    }),
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: MongoDBModel) => data.mongos.length < 2,
          tip: t('Proxy数量不足，至少 2 台'),
        },
      ],
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, MongoDBModel[]>>(() => ({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: props.selected.map(
      (item) =>
        ({
          id: item.id,
          master_domain: item.master_domain,
        }) as MongoDBModel,
    ),
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

  const { loading, run: queryCluster } = useRequest(filterClusters<MongoDBModel>, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          id: item.id,
          master_domain: item.master_domain,
          mongos: item.mongos,
          spec_config: item.mongos[0].spec_config,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      id: undefined,
      master_domain: value,
      mongos: [] as MongoDBModel['mongos'],
      spec_config: {} as MongoDBModel['mongos'][0]['spec_config'],
    };
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value,
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, MongoDBModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.MONGO_SHARED_CLUSTER]);
  };

  watch(
    () => modelValue.value.master_domain,
    (value) => {
      handleInputChange(value);
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
