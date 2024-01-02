<template>
  <BkLoading
    :loading="loading"
    style="height: 100%;">
    <BkResizeLayout
      class="search-result"
      collapsible
      placement="right">
      <template #main>
        <div class="search-result-head">
          <div class="search-result-search">
            <BkInput
              v-model="keyword"
              class="head-input"
              clearable>
              <template #suffix>
                <span class="input-icon suffix-icon">
                  <DbIcon type="search" />
                </span>
              </template>
            </BkInput>
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
            class="search-result-tab"
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
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import QuickSearchClusterDomainModel from '@services/model/quiker-search/quick-search-cluster-domain';
  import QuickSearchClusterNameModel from '@services/model/quiker-search/quick-search-cluster-name';
  import QuickSearchInstanceModel from '@services/model/quiker-search/quick-search-instance';
  import TaskFlowModel from '@services/model/taskflow/taskflow';
  import TicketModel from '@services/model/ticket/ticket';
  import { quickSearch } from '@services/source/quickSearch';

  import { useDebouncedRef } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import FilterOptions from '@components/system-search/components/search-result/FilterOptions.vue';

  import ClusterDomain from './components/ClusterDomain.vue';
  import ClusterName from './components/ClusterName.vue';
  import Instance from './components/Instance.vue';
  import ResourcePool from './components/ResourcePool.vue';
  import Task from './components/Task.vue';
  import Ticket from './components/Ticket.vue';

  const formatRouteQuery = () => {
    const {
      filter_type,
      bk_biz_ids: bkBizIds,
      db_types: dbTypes,
      resource_types: resourceTypes,
    } = route.query as unknown as {
      filter_type: string,
      bk_biz_ids?: string,
      db_types?: string,
      resource_types?: string,
    };

    return {
      bk_biz_ids: bkBizIds ? bkBizIds.split(',').map(bizId => Number(bizId)) : [],
      db_types: dbTypes ? dbTypes.split(',') : [],
      resource_types: resourceTypes ? resourceTypes.split(',') : [],
      filter_type,
    };
  };

  const route = useRoute();
  const { t } = useI18n();
  const { bizs: bizList } = useGlobalBizs();
  const keyword = useDebouncedRef(route.query.keyword as string || '');

  const comMap = {
    cluster_domain: ClusterDomain,
    cluster_name: ClusterName,
    instance: Instance,
    task: Task,
    resource_pool: ResourcePool,
    ticket: Ticket,
  };

  const dataMap = ref<{
    cluster_name: QuickSearchClusterNameModel[],
    cluster_domain: QuickSearchClusterDomainModel[],
    instance: QuickSearchInstanceModel[],
    task: TaskFlowModel[],
    resource_pool: DbResourceModel[],
    ticket: TicketModel[],
  }>({
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
    if (comMap[activeTab.value as keyof typeof comMap]) {
      return comMap[activeTab.value as keyof typeof comMap];
    }
    return ClusterDomain;
  });

  const dataList = computed(() => {
    if (dataMap.value[activeTab.value as keyof typeof comMap]) {
      return dataMap.value[activeTab.value as keyof typeof comMap];
    }
    return dataMap.value.cluster_domain;
  });

  const bizIdNameMap = computed<Record<number, string>>(() => bizList
    .reduce((result, item) => Object.assign(result, { [item.bk_biz_id]: item.name }), {}));

  const {
    loading,
    run: quickSearchRun,
  } = useRequest(quickSearch, {
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

  watch([keyword, formData], ([newKeyword, newFormData]) => {
    if (!newKeyword) {
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
      ...newFormData,
      keyword: newKeyword,
      limit: 1000,
    });
  }, {
    immediate: true,
    deep: true,
  });

  // const handleExportAllClusters = () => {

  // };

  // const handleExportAllHosts = () => {

  // };
</script>

<style lang="less" scoped>
.search-result {
  height: 100%;

  .search-result-head {
    height: 100%;
    background-color: #FFF;

    .search-result-search {
      display: flex;
      padding: 45px 0 32px;
      justify-content: center;

      .head-input {
        width: 600px;
        height: 40px;
      }

      .input-icon {
        padding-left: 6px;
        font-size: 14px;
        line-height: 38px;
        color: #979BA5;
      }

      .suffix-icon {
        padding-right: 6px;
      }

      .export-button {
        height: 40px;

        .export-icon {
          font-size: 16px;
        }
      }
    }

    .search-result-tab {
      border-bottom: none;

      :deep(.bk-tab-header) {
        justify-content: center;
      }

      :deep(.bk-tab-content) {
        padding: 0 !important;
      }

    }

    .tab-content {
      height: calc(100% - 162px);
      background-color: #f5f7fa;

      .tab-table {
        margin: 16px 24px;
      }
    }
  }

  .tab-filter-options {
    padding: 10px 12px;
    background-color: #fff;
  }
}
</style>
