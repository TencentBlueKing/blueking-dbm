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
  </div>
  <ClusterSelector
    v-model:is-show="isShowClusterSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="clusterSelectorValue"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script lang="tsx">
  export interface IClusterData {
    id: number;
    cluster_name: string;
    status: string;
    master_domain: string;
    cluster_type: string;
  }
</script>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  interface Props {
    modelValue: Array<number>
  }
  interface Emits{
    (e: 'update:modelValue', value: Array<number>): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      disabledRowConfig: {
        handler: (data: IClusterData) => data.status !== 'normal',
        tip: t('集群异常'),
      },
    },
  };

  const colums = [
    {
      label: t('集群'),
      field: 'master_domain',
    },
    {
      label: t('类型'),
      field: 'cluster_type',
      render: () => 'TendbCluster',
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
  const clusterSelectorValue = shallowRef<{[key: string]: Array<IClusterData>}>({ [ClusterTypes.TENDBCLUSTER]: [] });
  const targetClusterList = shallowRef<Array<IClusterData>>([]);

  let isInnerChange = false;
  const triggerChange = () => {
    isInnerChange = true;
    emits('update:modelValue', targetClusterList.value.map(item => item.id));
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

  watch(() => props.modelValue, () => {
    if (isInnerChange) {
      isInnerChange = false;
      return;
    }
    if (props.modelValue.length < 1) {
      targetClusterList.value = [];
    } else {
      fetchClusterData(props.modelValue);
    }
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
      [ClusterTypes.TENDBCLUSTER]: _.filter(result, item => item.cluster_type === ClusterTypes.TENDBCLUSTER),
    };
    triggerChange();
  };

  const handelClusterChange = (selected: { [key: string]: Array<IClusterData> }) => {
    targetClusterList.value = Object.keys(selected).reduce(
      (list: IClusterData[], key) => list.concat(...selected[key]),
      [],
    );
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
