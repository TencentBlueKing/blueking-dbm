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
  <div class="render-simple-cluster-list">
    <div class="search-box">
      <BkInput
        v-model="searchKey"
        :placeholder="$t('集群名称')" />
    </div>
    <BkLoading :loading="isLoading">
      <div
        v-for="item in tableData"
        :key="item.id"
        class="cluster-item"
        :class="{
          active: item.id === modelValue,
        }"
        @click="handleSelectCluster(item)">
        <RenderClusterStatus
          :data="item.status"
          :show-text="false" />
        <span
          v-overflow-tips
          class="text-overflow"
          style="margin-left: 4px">
          {{ item.cluster_name }}
        </span>
      </div>
    </BkLoading>
    <BkPagination
      v-if="tableData.length > 0"
      v-model="current"
      align="center"
      class="mt16"
      :count="count"
      :limit="10"
      :show-limit="false"
      :show-total-count="false"
      small />
    <div v-if="!isLoading && tableData.length < 1">
      <EmptyStatus
        :is-anomalies="isAnomalies"
        :is-searching="!!searchKey"
        @clear-search="handleClearSearch"
        @refresh="fetchData" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref, shallowRef, watch } from 'vue';

  import { useDebouncedRef } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  interface Props {
    modelValue: number;
    dataSource: (params: any) => Promise<any>;
  }

  interface Emits {
    (e: 'update:modelValue', value: number): void;
    (e: 'update:clusterType', value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const globalBizsStore = useGlobalBizs();

  const searchKey = useDebouncedRef('');

  const count = ref(0);
  const current = ref(1);

  const tableData = shallowRef<Array<any>>([]);
  const isLoading = ref(true);
  const isAnomalies = ref(false);

  const fetchData = () => {
    isLoading.value = true;
    props
      .dataSource({
        bk_biz_id: globalBizsStore.currentBizId,
        name: searchKey.value,
      })
      .then((data: { count: number; results: Array<{ id: number; cluster_type: string }> }) => {
        current.value = data.count;
        tableData.value = data.results;
        if (data.results.length < 1) {
          return;
        }
        const clusterIdMap = data.results.reduce(
          (result, item) => ({
            ...result,
            [item.id]: true,
          }),
          {} as Record<number, boolean>,
        );
        const currentCluster = clusterIdMap[props.modelValue];
        // 选中不在最新的表中，默认选择第一个
        if (!currentCluster) {
          handleSelectCluster(data.results[0]);
          return;
        }

        emits('update:clusterType', data.results.find((item) => item.id === props.modelValue)?.cluster_type ?? '');

        isAnomalies.value = false;
      })
      .catch(() => {
        current.value = 0;
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchData();

  watch(searchKey, () => {
    fetchData();
  });

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const handleSelectCluster = (data: any) => {
    emits('update:clusterType', data.cluster_type);

    if (props.modelValue === data.id) {
      return;
    }
    emits('update:modelValue', data.id);
  };
</script>
<style lang="less">
  .render-simple-cluster-list {
    .search-box {
      padding: 24px 20px 18px;
    }

    .cluster-item {
      display: flex;
      height: 35px;
      padding: 0 20px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      border-top: 1px solid transparent;
      border-bottom: 1px solid transparent;
      transition: all 0.15s;
      align-items: center;

      &:hover,
      &.active {
        background: #fff;
      }

      &.active {
        position: relative;
        cursor: default;
        border-top-color: #dcdee5;
        border-bottom-color: #dcdee5;

        &::after {
          position: absolute;
          top: 0;
          right: -1px;
          bottom: 0;
          width: 1px;
          background: #fff;
          content: '';
        }
      }
    }
  }
</style>
