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
  <div class="sql-execute-target-cluster">
    <DbFormItem
      ref="formItemRef"
      :label="t('目标集群')"
      property="cluster_ids"
      required
      :rules="rules">
      <BkButton @click="handleShowClusterSelector">
        <DbIcon
          style="margin-right: 3px;"
          type="add" />
        <span>{{ t('添加目标集群') }}</span>
      </BkButton>
      <div :class="{ 'cluster-checking': isLoading }">
        <BkLoading :loading="isLoading">
          <DbOriginalTable
            v-if="targetClusterList.length > 0"
            class="mt-16"
            :columns="colums"
            :data="targetClusterList" />
        </BkLoading>
      </div>
    </DbFormItem>
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGO_REPLICA_SET]"
      :selected="clusterSelectorValue"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import { ClusterTypes } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import ClusterSelector, {
    type TabItem,
  } from '@components/cluster-selector-new/Index.vue';

  const modelValue = defineModel<number[]>();

  const { t } = useI18n();

  const isLoading = ref(false);
  const isShowClusterSelector = ref(false);
  const formItemRef = ref();
  const clusterSelectorValue = shallowRef<{ [key: string]: MongodbModel[] }>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    [ClusterTypes.MONGO_REPLICA_SET]: [],
  });
  const targetClusterList = shallowRef<Array<MongodbModel>>([]);


  const tabListConfig = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const colums = [
    {
      label: t('集群'),
      field: 'master_domain',
    },
    {
      label: t('集群类型'),
      field: 'cluster_type',
      render: ({ data }: {data: MongodbModel}) => data.clusterTypeText,
    },
    {
      label: t('状态'),
      render: ({ data }: {data: MongodbModel}) => (
        <RenderClusterStatus data={data.status} />
      ),
    },
    {
      label: t('操作'),
      width: '100',
      field: 'action',
      render: ({ data }: {data: MongodbModel}) => (
        <bk-button
          theme="primary"
          text
          onClick={() => handleRemove(data)}>
          { t('删除') }
        </bk-button>
      ),
    },
  ];

  const rules = [
    {
      validator: (value: number[]) => value.length > 0,
      message: t('目标集群不能为空'),
      trigger: 'change',
    },
  ];

  const triggerChange = () => {
    modelValue.value = targetClusterList.value.map(item => item.id);
  };

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handleRemove = (row: MongodbModel) => {
    const list: MongodbModel[] = [];
    clusterSelectorValue.value[ClusterTypes.MONGO_REPLICA_SET] = [];
    clusterSelectorValue.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];

    targetClusterList.value.forEach((item) => {
      if (item.id !== row.id) {
        list.push(item);
        clusterSelectorValue.value[item.cluster_type].push(item);
      }
    });

    triggerChange();
  };

  const handelClusterChange = (selected: { [key: string]: Array<MongodbModel> }) => {
    formItemRef.value.clearValidate();
    clusterSelectorValue.value = selected;
    targetClusterList.value = _.flatMap(Object.values(selected));
    triggerChange();
  };
</script>
<style lang="less">
  .sql-execute-target-cluster {
    display: block;
    margin-top: 16px;
    margin-bottom: 24px;

    .cluster-checking {
      height: 86px;
    }
  }
</style>
