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
          style="margin-right: 3px"
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
      :cluster-types="clusterTypeList"
      :selected="clusterSelectorValue"
      @change="handelClusterChange" />
  </div>
</template>
<script lang="tsx">
  export interface IClusterData {
    id: number;
    cluster_name: string;
    status: string;
    major_version: string;
    master_domain: string;
    cluster_type: string;
  }
</script>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    clusterTypeList: ClusterTypes[]
  }

  defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const modelValue = defineModel<number[]>({
    required: true,
    default: () => [],
  })
  const clusterVersionList = defineModel<string[]>('clusterVersionList',{
    default: () => [],
  })

  const colums = [
    {
      label: t('集群'),
      field: 'master_domain',
    },
    {
      label: t('类型'),
      field: 'cluster_type',
      render: ({ data }: {data: IClusterData}) => (data.cluster_type === 'tendbha' ? t('主从') : t('单节点')),
    },
    {
      label: t('版本'),
      render: ({ data }: {data: IClusterData}) => data.major_version || '--',
    },
    {
      label: t('状态'),
      render: ({ data }: {data: IClusterData}) => (
        <RenderClusterStatus data={data.status} />
      ),
    },
    {
      label: t('操作'),
      width: '100',
      field: 'action',
      render: ({ data }: {data: IClusterData}) => (
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

  const isLoading = ref(false);
  const isShowClusterSelector = ref(false);
  const formItemRef = ref();
  const clusterSelectorValue = shallowRef<Record<string, TendbhaModel[] | TendbsingleModel[]>>({
    [ClusterTypes.TENDBHA]: [] as TendbhaModel[],
    [ClusterTypes.TENDBSINGLE]: [] as TendbsingleModel[],
  });
  const targetClusterList = shallowRef<Array<IClusterData>>([]);

  let isInnerChange = false;
  const triggerChange = () => {
    isInnerChange = true;
    modelValue.value = targetClusterList.value.map(item => item.id);
    clusterVersionList.value = _.uniq(targetClusterList.value.map(item => item.major_version));
  };

  const fetchClusterData = (clusterIds: number[]) => {
    isLoading.value = true;
    queryClusters({
      cluster_filters: clusterIds.map(id => ({
        id,
      })),
      bk_biz_id: currentBizId,
    })
      .then((data) => {
        targetClusterList.value = data;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  watch(modelValue, () => {
    if (isInnerChange) {
      isInnerChange = false;
      return;
    }
    if (modelValue.value.length < 1) {
      targetClusterList.value = [];
    } else {
      fetchClusterData(modelValue.value);
    }
  }, {
    immediate: true,
  });

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handleRemove = (clusterData: IClusterData) => {
    const result = targetClusterList.value.reduce((result, item) => {
      if (item.id !== clusterData.id) {
        result.push(item);
      }
      return result;
    }, [] as IClusterData[]);

    targetClusterList.value = result;

    // ClusterSelector 的值回填
    clusterSelectorValue.value = {
      [ClusterTypes.TENDBHA]: _.filter(result, item => item.cluster_type === 'tendbha') as TendbhaModel[],
      [ClusterTypes.TENDBSINGLE]: _.filter(result, item => item.cluster_type === 'tendbsingle') as TendbsingleModel[],
    };
    triggerChange();
  };

  const handelClusterChange = (selected: Record<string, TendbhaModel[] | TendbsingleModel[]>) => {
    console.log('selected = ', selected)
    targetClusterList.value = _.flatten(Object.values(selected))
    console.log('targetClusterList.value = ', targetClusterList.value)
    formItemRef.value.clearValidate();
    clusterSelectorValue.value = selected;
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
