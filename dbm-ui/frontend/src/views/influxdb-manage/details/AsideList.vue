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
  <div class="influxdb-details-aside">
    <BkInput
      v-model="searchKey"
      class="aside-search"
      clearable
      :placeholder="$t('实例')"
      type="search"
      @clear="handleClearSearch"
      @enter="fetchList" />
    <BkLoading
      class="aside-loading"
      :loading="isLoading">
      <div class="aside-list db-scroll-y">
        <template v-if="listData.length !== 0">
          <div
            v-for="item of listData"
            :key="item.id"
            class="aside-list__item"
            :class="[{
              'aside-list__item--active': item.id === activeInstId
            }]"
            @click="handleClickItem(item)">
            <DbStatus :theme="getItemStatus(item)" />
            <span
              v-overflow-tips="{ content: item.instance_address, placement: 'right' }"
              class="text-overflow">
              {{ item.instance_address }}
            </span>
          </div>
        </template>
        <EmptyStatus
          v-else
          :is-anomalies="isAnomalies"
          :is-searching="!!searchKey"
          @clear-search="handleClearSearch"
          @refresh="fetchList" />
      </div>
      <BkPagination
        v-model="pagination.current"
        align="center"
        class="aside-pagination"
        :count="pagination.count"
        :limit="pagination.limit"
        :limit-list="[50]"
        :show-total-count="false"
        small
        @change="handleChangePage" />
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { getListInstance } from '@services/influxdb';
  import type InfluxdbInstanceModel from '@services/model/influxdb/influxdbInstance';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { useGlobalBizs } from '@/stores';

  interface Emits {
    (e: 'change', value: { id: number, instance: string }): void
  }

  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  let isInit = true;
  const isLoading = ref(false);
  const isAnomalies = ref(false);
  const searchKey = ref('');
  const activeInstId = ref(0);
  const listData = ref<InfluxdbInstanceModel[]>([]);
  const pagination = reactive({
    limit: 50,
    current: 1,
    count: 0,
  });

  /**
   * 获取状态
   */
  const getItemStatus = (data: InfluxdbInstanceModel) => {
    const statusMap = {
      running: 'success',
      unavailable: 'danger',
      restoring: 'loading',
    };
    return statusMap[data.status as keyof typeof statusMap] || 'danger';
  };

  const fetchList = () => {
    isLoading.value = true;
    getListInstance({
      bk_biz_id: currentBizId,
      limit: pagination.limit,
      offset: pagination.limit * (pagination.current - 1),
      instance_address: searchKey.value,
    })
      .then((data) => {
        listData.value = data.results;
        isAnomalies.value = false;

        const targetItem = listData.value.find(item => item.id === Number(route.params.instId));
        if (isInit && targetItem) {
          handleClickItem(targetItem);
          return;
        }

        if (!targetItem && listData.value[0]) {
          handleClickItem(listData.value[0]);
        }
      })
      .catch(() => {
        listData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
        isInit = false;
      });
  };

  fetchList();

  /**
   * 翻页
   */
  const handleChangePage = (value: number) => {
    pagination.current = value;
    fetchList();
  };

  const handleClearSearch = () => {
    searchKey.value = '';
    fetchList();
  };

  /**
   * 选中列表项
   */
  const handleClickItem = (data: InfluxdbInstanceModel) => {
    activeInstId.value = data.id;
    emits('change', {
      id: data.id,
      instance: data.instance_address,
    });

    router.replace({
      params: {
        instId: data.id,
      },
    });
  };
</script>

<style lang="less" scoped>
.influxdb-details-aside {
  position: relative;
  height: 100%;
  padding-top: 24px;

  .aside-loading {
    height: calc(100% - 56px);
  }

  .aside-search {
    display: flex;
    width: calc(100% - 40px);
    margin: 0 auto 24px;
  }

  .aside-list {
    height: calc(100% - 32px);

    &__item {
      display: flex;
      width: calc(100% - 1px);
      padding: 0 20px;
      font-size: @font-size-mini;
      line-height: 32px;
      cursor: pointer;
      border-top: 1px solid transparent;
      border-bottom: 1px solid transparent;
      align-items: center;

      &:hover {
        background-color: @bg-white;
      }

      &--active {
        width: 100%;
        background-color: @bg-white;
        border-top-color: @border-disable;
        border-bottom-color: @border-disable;
      }
    }
  }

  .aside-pagination {
    padding: 4px 0;

    :deep(.bk-pagination-limit) {
      display: none;
    }
  }
}
</style>
