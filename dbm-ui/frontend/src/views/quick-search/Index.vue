<template>
  <BkResizeLayout
    class="quick-search"
    collapsible
    :initial-divide="320"
    :max="500"
    :min="300"
    placement="right"
    style="height: 100%">
    <template #main>
      <div class="quick-search-head">
        <div class="quick-search-search">
          <SearchInput @search="handleSearch" />
        </div>
        <BkTab
          v-model:active="activeTab"
          class="quick-search-tab"
          type="unborder-card">
          <BkTabPanel
            v-for="item in panelList"
            :key="item.name"
            :label="item.label"
            :name="item.name">
            <template #label>
              <div>{{ item.label }} ( {{ item.count }} )</div>
            </template>
          </BkTabPanel>
        </BkTab>
        <div class="tab-content">
          <BkLoading
            class="tab-content-loading"
            :loading="loading">
            <ScrollFaker>
              <KeepAlive>
                <Component
                  :is="renderComponent"
                  ref="renderComponent"
                  :biz-id-name-map="bizIdNameMap"
                  class="tab-table"
                  :form-data="formData"
                  :keyword="keyword"
                  @clear-search="handleClearSearch" />
              </KeepAlive>
            </ScrollFaker>
          </BkLoading>
        </div>
      </div>
    </template>
    <template #aside>
      <ScrollFaker class="tab-filter-options">
        <FilterOptions
          v-model="formData"
          :biz-list="bizList"
          db-options-expand />
      </ScrollFaker>
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import { storeToRefs } from 'pinia';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { quickSearch } from '@services/source/quickSearch';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs, useSystemSearchStore } from '@stores';

  import { FilterType } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import FilterOptions from '@components/system-search/components/search-result/FilterOptions.vue';

  import Cluster from './components/content/cluster/Index.vue';
  import Instance from './components/content/instance/Index.vue';
  import Machine from './components/content/Machine.vue';
  import Task from './components/content/Task.vue';
  import Ticket from './components/content/Ticket.vue';
  import SearchInput from './components/SearchInput.vue';

  type MapArrayToString<T> = {
    [K in keyof T]: T[K] extends Array<string | number> ? string : T[K];
  };

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { bizs: bizList } = useGlobalBizs();
  const { getSearchParams, removeSearchParam, replaceSearchParams } = useUrlSearch();
  const systemSearchStore = useSystemSearchStore();

  // 使用 store 中的状态
  const { formData, keyword } = storeToRefs(systemSearchStore);

  let isRedirectSearch = true;
  let routeParamsMemo = {};

  const comMap = {
    cluster: Cluster,
    instance: Instance,
    machine: Machine,
    task: Task,
    ticket: Ticket,
  };

  const bizIdNameMap = bizList.reduce(
    (result, item) => Object.assign(result, { [item.bk_biz_id]: item.name }),
    {} as Record<number, string>,
  );

  const renderComponentRef = useTemplateRef('renderComponent');

  // const keyword = ref((route.query.keyword as string) || '');
  // const dataMap = ref<Omit<ServiceReturnType<typeof quickSearch>, 'keyword' | 'short_code'>>({
  //   cluster: [],
  //   instance: [],
  //   machine: [],
  //   task: [],
  //   ticket: [],
  // });

  const activeTab = ref('cluster');
  const panelList = reactive([
    {
      count: 0,
      label: t('集群'),
      name: 'cluster',
    },
    {
      count: 0,
      label: t('实例'),
      name: 'instance',
    },
    {
      count: 0,
      label: t('主机'),
      name: 'machine',
    },
    {
      count: 0,
      label: t('任务'),
      name: 'task',
    },
    {
      count: 0,
      label: t('单据'),
      name: 'ticket',
    },
  ]);

  const renderComponent = computed(() => {
    if (loading.value) {
      return null;
    }

    const activeComponent = comMap[activeTab.value as keyof typeof comMap];

    if (activeComponent) {
      return activeComponent;
    }
    return Cluster;
  });

  // const dataList = computed(() => {
  //   if (loading.value) {
  //     return [];
  //   }
  //   const activeDataList = dataMap.value[activeTab.value as keyof typeof comMap];
  //   if (activeDataList) {
  //     return activeDataList;
  //   }
  //   return dataMap.value.cluster;
  // });

  const { loading, run: quickSearchRun } = useRequest(quickSearch, {
    manual: true,
    onAfter() {
      isRedirectSearch = false;
    },
    onSuccess(data, params) {
      if (isRedirectSearch) {
        isRedirectSearch = false;
        keyword.value = data.keyword.replace(batchSplitRegex, '|');
        handleSearch();
      }

      panelList[0].count = data.count.cluster;
      panelList[1].count = data.count.instance;
      panelList[2].count = data.count.machine;
      panelList[3].count = data.count.task;
      panelList[4].count = data.count.ticket;

      const currentPanelItem = panelList.find((panel) => panel.name === activeTab.value);
      if (currentPanelItem && currentPanelItem.count === 0) {
        const panelItem = panelList.find((panel) => panel.count > 0);
        if (panelItem) {
          activeTab.value = panelItem.name;
        }
      }

      const serachParams = Object.entries(params[0]).reduce<Record<string, MapArrayToString<(typeof params)[0]>>>(
        (prev, [key, value]) => {
          if (Array.isArray(value)) {
            return Object.assign(prev, { [key]: value.join(',') });
          }
          return Object.assign(prev, { [key]: value });
        },
        {},
      );
      Object.assign(serachParams, {
        short_code: data.short_code,
      });
      delete serachParams.keyword;
      routeParamsMemo = {
        ...routeParamsMemo,
        ...serachParams,
      };

      replaceSearchParams(routeParamsMemo);
    },
  });

  watch(
    formData,
    () => {
      handleSearch();
    },
    {
      deep: true,
    },
  );

  const handleSearch = () => {
    if (!keyword.value) {
      return;
    }

    // 只做数量展示和url联动
    quickSearchRun({
      ...formData.value,
      keyword: keyword.value.replace(batchSplitRegex, ' '),
      limit: 10,
    });

    renderComponentRef.value?.fetchData();
  };

  // watch(
  //   keyword,
  //   (newKeyword, oldKeyword) => {
  //     const newKeywordArr = newKeyword.split(batchSplitRegex);
  //     const oldKeywordArr = (oldKeyword || '').split(batchSplitRegex);

  //     if (!_.isEqual(newKeywordArr, oldKeywordArr) && !newKeyword.endsWith('\n')) {
  //       handleSearch();
  //     }
  //   },
  //   {
  //     immediate: true,
  //   },
  // );

  // const handleExportAllClusters = () => {

  // };

  // const handleExportAllHosts = () => {

  // };

  const handleClearSearch = () => {
    keyword.value = '';
    formData.value.bk_biz_ids = [];
    formData.value.db_types = [];
    formData.value.resource_types = [];
  };

  // 初始化查询
  const initRetrieve = () => {
    const formatRouteQuery = (initParams: Record<string, string>) => {
      const {
        bk_biz_ids: bkBizIds,
        db_types: dbTypes,
        filter_type: filterType,
        resource_types: resourceTypes,
      } = initParams;

      return {
        bk_biz_ids: bkBizIds ? bkBizIds.split(',').map((bizId) => Number(bizId)) : [],
        db_types: dbTypes ? dbTypes.split(',') : [],
        filter_type: (filterType as FilterType) || FilterType.EXACT,
        resource_types: resourceTypes ? resourceTypes.split(',') : [],
      };
    };
    const initParams = getSearchParams();
    routeParamsMemo = initParams;
    Object.assign(formData.value, formatRouteQuery(initParams));
    const shortCode = initParams?.short_code || initParams?.keyword;
    if (initParams?.tabName) {
      activeTab.value = initParams?.tabName || 'cluster';
      removeSearchParam('tabName');
    }
    if (shortCode) {
      // 只做数量查询，不做结果展示
      quickSearchRun({
        ...formData.value,
        limit: 10,
        short_code: shortCode,
      });
    }
  };
  initRetrieve();

  // 监听顶部搜索组件的刷新请求（结果页场景）
  watch(
    () => systemSearchStore.shouldRefresh,
    (shouldRefreshVal) => {
      if (!shouldRefreshVal) {
        return;
      }
      // keyword.value = systemSearchStore.keyword;
      systemSearchStore.consumeRefresh();
      handleSearch();
    },
  );

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.back();
        return;
      }
      router.push({
        name: route.query.from as string,
      });
    },
  });
</script>

<style lang="less">
  .quick-search {
    height: 100%;

    .quick-search-head {
      height: 100%;
      background-color: #fff;

      .quick-search-search {
        display: flex;
        padding: 45px 0 32px;
        justify-content: center;

        .export-button {
          height: 40px;

          .export-icon {
            font-size: 16px;
          }
        }
      }

      .quick-search-tab {
        box-shadow: 0 2px 4px 0 #1919290d;

        .bk-tab-header {
          justify-content: center;
          border-bottom: none;
        }

        .bk-tab-content {
          padding: 0 !important;
        }
      }

      .tab-content {
        height: calc(100% - 150px);
        background-color: #f5f7fa;

        .tab-content-loading {
          height: 100%;
          padding: 16px 0;

          .bk-loading-mask {
            z-index: 3 !important;
          }

          .bk-loading-indicator {
            z-index: 3 !important;
          }
        }

        .tab-table {
          margin: 0 24px;
        }
      }
    }

    .tab-filter-options {
      padding: 10px 12px;
      background-color: #fff;
    }

    .bk-resize-collapse {
      z-index: 3;
    }
  }

  .quick-search-empty {
    background-color: #fff;
  }
</style>
