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
  <MainBreadcrumbs>
    <template #append>
      <div class="status">
        <span class="status__label">{{ $t('状态') }}：</span>
        <span class="status__value">
          <DbStatus :theme="statusInfo.theme">{{ statusInfo.text }}</DbStatus>
        </span>
      </div>
    </template>
  </MainBreadcrumbs>
  <BkResizeLayout
    :border="false"
    class="cluster-details"
    collapsible
    initial-divide="280px"
    :max="380"
    :min="280">
    <template #aside>
      <AsideList
        ref="asideListRef"
        :active-item="state.details"
        :data="listState.data"
        :limit="listState.pagination.limit"
        :loading="listState.isLoading"
        :total="listState.pagination.count"
        @change-page="handleChangePage"
        @item-selected="handleClickItem"
        @return-page="handleChangePage"
        @search-clear="handleSearchChange"
        @search-enter="handleSearchChange" />
    </template>
    <template #main>
      <div class="cluster-details__main">
        <DbCard
          class="cluster-details__base"
          mode="collapse"
          :title="$t('基本信息')">
          <BkLoading :loading="state.isLoading">
            <EditInfo
              :columns="columns"
              :data="state.details" />
          </BkLoading>
        </DbCard>
        <BkTab
          v-model:active="state.activeTab"
          class="cluster-details__tab"
          type="unborder-card">
          <BkTabPanel
            :label="$t('集群拓扑')"
            name="topo">
            <ClusterTopo
              :id="activeId"
              :cluster-type="DBTypes.REDIS"
              :db-type="DBTypes.REDIS" />
          </BkTabPanel>
          <BkTabPanel
            :label="$t('变更记录')"
            name="event">
            <EventChange :id="activeId" />
          </BkTabPanel>
          <BkTabPanel
            :label="$t('监控仪表盘')"
            name="monitor">
            <MonitorDashboard
              :id="activeId"
              :cluster-type="state.details.cluster_type" />
          </BkTabPanel>
        </BkTab>
      </div>
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getResourceDetails } from '@services/clusters';
  import type { ResourceRedisItem } from '@services/types/clusters';

  import { useDefaultPagination } from '@hooks';

  import {
    useGlobalBizs,
    useMainViewStore,
  } from '@stores';

  import { DBTypes } from '@common/const';

  import AsideList from '@components/cluster-details/AsideList.vue';
  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import EventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';
  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';
  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  import type { RedisState } from '../common/types';
  import { useRedisData } from '../hooks/useRedisData';

  // 设置主视图padding
  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;
  mainViewStore.customBreadcrumbs = true;

  const globalBizsStore = useGlobalBizs();
  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const state = reactive({
    isLoading: false,
    details: {} as ResourceRedisItem,
    search: '',
    activeTab: 'topo',
  });
  const columns:InfoColumn[][] = [
    [{
      label: t('集群名称'),
      key: 'cluster_name',
    }, {
      label: t('集群别名'),
      key: 'cluster_alias',
    }, {
      label: t('域名'),
      key: 'master_domain',
    }],
    [{
      label: t('架构版本'),
      key: 'cluster_type_name',
    }, {
      label: t('数据库版本'),
      key: 'major_version',
    }, {
      label: t('地域'),
      key: 'region',
    }],
    [{
      label: t('创建人'),
      key: 'creator',
    }, {
      label: t('创建时间'),
      key: 'create_at',
    }],
  ];
  const statusInfo = computed(() => {
    const { status } = state.details;
    if (status === 'normal') return {
      theme: 'success',
      text: t('正常'),
    };

    return {
      theme: 'danger',
      text: t('异常'),
    };
  });

  /** 侧栏功能 */
  const listState = reactive<RedisState>({
    isAnomalies: false,
    isInit: true,
    isLoading: false,
    data: [],
    selected: [],
    searchValues: [],
    pagination: useDefaultPagination(),
  });
  // 获取侧栏列表数据
  const { fetchResources } = useRedisData(listState);
  const asideListRef = ref<InstanceType<typeof AsideList> | null>(null);
  const activeId = computed(() => Number(route.params.id));
  // 列表有数据 & 非搜索状态 & 列表非loading状态
  // const showReturnIcon = computed(() => listState.data.length > 0 && !state.search && listState.isLoading === false);

  onMounted(async () => {
    listState.pagination.limit = 50; // 设置默认为每页50条数据
    try {
      const results = await Promise.allSettled([fetchResources(), fetchResourceDetails(activeId.value)]);
      const detailsResult = results[1];
      if (detailsResult.status !== 'rejected') {
        const target = listState.data.find(item => item.id === activeId.value);
        // 记录当前选中项在第几页
        asideListRef.value?.setActiveLocationPage(1);
        if (target === undefined) {
          // 确保 details 赋值成功后再添加
          setTimeout(() => {
            listState.data.unshift(state.details);
          });
        }
      }
    } catch (e) {
      console.error(e);
    }
  });

  /**
   * 获取集群详情
   */
  function fetchResourceDetails(id: number) {
    const params = {
      type: DBTypes.REDIS,
      bk_biz_id: globalBizsStore.currentBizId,
      id,
    };
    state.isLoading = true;
    getResourceDetails<ResourceRedisItem>(DBTypes.REDIS, params)
      .then((res) => {
        state.details = res;
        mainViewStore.$patch({
          breadCrumbsTitle: t('xx集群详情【inst】', { title: 'Redis', inst: state.details.master_domain }),
        });
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  /**
   * 切换集群
   */
  function handleClickItem(data: ResourceRedisItem) {
    if (listState.isLoading) return;

    const { id } = data;
    router.replace({ params: { id } });
    fetchResourceDetails(id);
  }

  /**
   * 翻页
   */
  function handleChangePage(page: number) {
    listState.pagination.current = page;
    fetchResources({ domain: state.search })
      .then(() => {
        if (!state.search) {
          // 非搜索状态的时候，记录选中项在第几页
          const target = listState.data.find(item => item.id === activeId.value);
          if (target) {
            asideListRef.value?.setActiveLocationPage(page);
          }

          // 记录选中项在第一页 & 处于第一页 & 没有找到选中内容，将选中项置顶到第一页
          if (asideListRef.value?.isInsertToPage() && target === undefined) {
            listState.data.unshift(state.details);
          }
        }
      });
  }

  /**
   * 侧栏搜索
   */
  function handleSearchChange(value: string) {
    state.search = value;
    handleChangePage(1);
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .status {
    .flex-center();
  }

  .cluster-details {
    height: calc(100% - 52px);

    :deep(.bk-resize-layout-aside-content) {
      width: calc(100% + 1px);
    }

    &__main {
      height: 100%;
      flex-direction: column;

      .flex-center();

      .db-card {
        width: 100%;
      }
    }

    &__tab {
      width: 100%;
      overflow: hidden;
      background-color: white;
      flex: 1;

      :deep(.bk-tab-header) {
        margin: 0 24px;
      }

      :deep(.bk-tab-content) {
        height: calc(100% - 42px);
        padding: 0;
      }
    }
  }
</style>
