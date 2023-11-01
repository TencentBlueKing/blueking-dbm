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
  <div class="db-backup-targer-cluster">
    <BkFormItem
      ref="formItemRef"
      :label="t('目标集群')"
      property="cluster_ids"
      required
      :rules="rules">
      <BkButton @click="handleShowClusterSelector">
        <DbIcon type="add" />
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
    </BkFormItem>
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :get-resource-list="getList"
      :selected="{}"
      :tab-list="clusterSelectorTabList"
      @change="handelClusterChange" />
  </div>
</template>
<script lang="tsx">
  export interface IClusterData {
    id: number,
    cluster_name: string,
    status: string,
    master_domain: string,
  }
</script>
<script setup lang="tsx">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';
  import { getList } from '@services/source/resourceSpider';

  import { useGlobalBizs } from '@stores';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import ClusterSelector from '@components/cluster-selector/SpiderClusterSelector.vue';

  import { ClusterTypes } from '@/common/const';

  interface Props {
    modelValue: Array<number>
  }
  interface Emits{
    (e: 'update:modelValue', value: Array<number>): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const clusterSelectorTabList = [{
    id: ClusterTypes.SPIDER,
    name: '集群',
  }];

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const formItemRef = ref();
  const colums = [
    {
      label: t('集群'),
      field: 'cluster_name',
    },
    {
      label: t('节点类型'),
      field: 'cluster_name',
    },
    {
      label: t('集群'),
      field: 'cluster_name',
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
    triggerChange();
  };

  const handelClusterChange = (selected: { [key: string]: Array<IClusterData> }) => {
    targetClusterList.value = Object.keys(selected).reduce(
      (list: IClusterData[], key) => list.concat(...selected[key]),
      [],
    );
    formItemRef.value.clearValidate();
    triggerChange();
  };
</script>
<style lang="less">
  .db-backup-targer-cluster {
    display: block;
    margin-top: 16px;
    margin-bottom: 24px;

    .cluster-checking {
      height: 86px;
    }
  }
</style>
