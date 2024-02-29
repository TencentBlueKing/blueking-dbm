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
          <SearchInput
            v-model="keyword"
            @search="handleSearch" />
          <!-- <BkDropdown class="ml-8">
                <BkButton
                  class="export-button"
                  size="large">
                  {{ t('导出') }}
                  <DbIcon
                    class="export-icon ml-12"
                    type="down-big" />
                </BkButton>
                <template #content>
                  <BkDropdownMenu>
                    <BkDropdownItem @click="handleExportAllClusters">
                      {{ t('所有集群') }}
                    </BkDropdownItem>
                    <BkDropdownItem @click="handleExportAllHosts">
                      {{ t('所有主机') }}
                    </BkDropdownItem>
                  </BkDropdownMenu>
                </template>
              </BkDropdown> -->
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
                  :biz-id-name-map="bizIdNameMap"
                  class="tab-table"
                  :data="dataList"
                  :keyword="keyword" />
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { quickSearch } from '@services/source/quickSearch';

  import { useDebouncedRef } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import FilterOptions from '@components/system-search/components/search-result/FilterOptions.vue';

  import ClusterDomain from './components/ClusterDomain.vue';
  import ClusterName from './components/ClusterName.vue';
  import Instance from './components/Instance.vue';
  import ResourcePool from './components/ResourcePool.vue';
  import SearchInput from './components/SearchInput.vue';
  import Task from './components/Task.vue';
  import Ticket from './components/Ticket.vue';

  const formatRouteQuery = () => {
    const {
      filter_type,
      bk_biz_ids: bkBizIds,
      db_types: dbTypes,
      resource_types: resourceTypes,
    } = route.query as unknown as {
      filter_type: string;
      bk_biz_ids?: string;
      db_types?: string;
      resource_types?: string;
    };

    return {
      bk_biz_ids: bkBizIds ? bkBizIds.split(',').map((bizId) => Number(bizId)) : [],
      db_types: dbTypes ? dbTypes.split(',') : [],
      resource_types: resourceTypes ? resourceTypes.split(',') : [],
      filter_type,
    };
  };

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { bizs: bizList } = useGlobalBizs();
  const keyword = useDebouncedRef((route.query.keyword as string) || '');

  const comMap = {
    cluster_domain: ClusterDomain,
    cluster_name: ClusterName,
    instance: Instance,
    task: Task,
    resource_pool: ResourcePool,
    ticket: Ticket,
  };

  const bizIdNameMap = bizList.reduce(
    (result, item) => Object.assign(result, { [item.bk_biz_id]: item.name }),
    {} as Record<number, string>,
  );

  const dataMap = ref<Omit<ServiceReturnType<typeof quickSearch>, 'machine'>>({
    cluster_name: [],
    cluster_domain: [],
    instance: [],
    task: [],
    resource_pool: [],
    ticket: [],
  });

  const formData = ref(formatRouteQuery());
  const activeTab = ref('cluster_domain');
  const panelList = reactive([
    {
      name: 'cluster_domain',
      label: t('域名'),
      count: 0,
    },
    {
      name: 'cluster_name',
      label: t('集群'),
      count: 0,
    },
    {
      name: 'instance',
      label: t('实例'),
      count: 0,
    },
    {
      name: 'resource_pool',
      label: t('资源池主机'),
      count: 0,
    },
    {
      name: 'task',
      label: t('历史任务'),
      count: 0,
    },
    {
      name: 'ticket',
      label: t('单据'),
      count: 0,
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
    return ClusterDomain;
  });

  const dataList = computed(() => {
    if (loading.value) {
      return [];
    }
    const activeDataList = dataMap.value[activeTab.value as keyof typeof comMap];
    if (activeDataList) {
      return activeDataList;
    }
    return dataMap.value.cluster_domain;
  });

  const { loading, run: quickSearchRun } = useRequest(quickSearch, {
    manual: true,
    onSuccess(data) {
      Object.assign(dataMap.value, {
        cluster_domain: data.cluster_domain,
        cluster_name: data.cluster_name,
        instance: data.instance,
        task: data.task,
        resource_pool: data.resource_pool,
        ticket: data.ticket,
      });
      panelList[0].count = data.cluster_domain.length;
      panelList[1].count = data.cluster_name.length;
      panelList[2].count = data.instance.length;
      panelList[3].count = data.resource_pool.length;
      panelList[4].count = data.task.length;
      panelList[5].count = data.ticket.length;
    },
  });

  const handleSearch = () => {
    if (!keyword.value) {
      Object.assign(dataMap.value, {
        cluster_domain: [],
        cluster_name: [],
        instance: [],
        task: [],
        resource_pool: [],
        ticket: [],
      });
      panelList[0].count = 0;
      panelList[1].count = 0;
      panelList[2].count = 0;
      panelList[3].count = 0;
      panelList[4].count = 0;
      panelList[5].count = 0;

      return;
    }

    quickSearchRun({
      ...formData.value,
      keyword: keyword.value.replace(/，/g, '\n'),
      limit: 1000,
    });
  };

  watch(
    keyword,
    (newKeyword, oldKeyword) => {
      const newKeywordArr = newKeyword.split(/，|\n/g);
      const oldKeywordArr = (oldKeyword || '').split(/，|\n/g);

      if (!_.isEqual(newKeywordArr, oldKeywordArr) && !newKeyword.endsWith('\n')) {
        handleSearch();
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    formData,
    () => {
      handleSearch();
    },
    {
      deep: true,
    },
  );

  // const handleExportAllClusters = () => {

  // };

  // const handleExportAllHosts = () => {

  // };

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

<style lang="less" scoped>
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

        :deep(.bk-tab-header) {
          justify-content: center;
          border-bottom: none;
        }

        :deep(.bk-tab-content) {
          padding: 0 !important;
        }
      }

      .tab-content {
        height: calc(100% - 162px);
        background-color: #f5f7fa;

        :deep(.tab-content-loading) {
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

    :deep(.bk-resize-collapse) {
      z-index: 3;
    }
  }
</style>
