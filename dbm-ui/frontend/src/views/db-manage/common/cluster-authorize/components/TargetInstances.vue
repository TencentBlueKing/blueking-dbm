<template>
  <BkFormItem
    ref="formRef"
    v-model="targetInstances"
    class="cluster-authorize-bold"
    :label="t('目标集群')"
    property="target_instances"
    required
    :rules="rules">
    <BkButton
      class="cluster-authorize-button"
      @click="handleShowTargetCluster">
      <DbIcon
        class="button-icon"
        type="db-icon-add" />
      {{ t('添加目标集群') }}
    </BkButton>
    <div
      v-if="state.tableData.length > 0"
      class="target-cluster-table mt-16"
      :class="{ 'target-cluster-table-expand': collapse }">
      <div
        class="target-cluster-table-header"
        @click="handleToggle">
        <div class="target-cluster-table-left">
          <i class="db-icon-down-shape target-cluster-table-icon" />
          <div class="target-cluster-table-title">
            <strong>【{{ tabListConfigMap[state.clusterType].name }}】</strong>
            <span> - </span>
            <I18nT
              keypath="共n个"
              tag="p">
              <strong style="color: #3a84ff">{{ state.tableData.length }}</strong>
            </I18nT>
          </div>
        </div>
        <BkDropdown
          class="target-cluster-table-dropdown"
          :popover-options="{
            clickContentAutoHide: true,
          }"
          trigger="click"
          @click.stop>
          <i class="db-icon-more target-cluster-table-trigger" />
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem
                v-for="(item, index) of operations"
                :key="index"
                @click="item.onClick()">
                {{ item.label }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
      <Transition mode="in-out">
        <div
          v-show="collapse"
          class="target-cluster-table-content">
          <PrimaryTable
            :data="renderData"
            row-key="id">
            <TableColumn
              col-key="master_domain"
              :title="t('域名')">
              <template #default="{ row }">
                <div
                  v-if="row.isMaster !== undefined"
                  class="domain-column">
                  <span :class="row.isMaster ? 'master-icon' : 'slave-icon'">
                    {{ row.isMaster ? t('主') : t('从') }}
                  </span>
                  <span class="ml-6">{{ row.master_domain }}</span>
                </div>
                <span v-else>{{ row.master_domain }}</span>
              </template>
            </TableColumn>
            <TableColumn
              col-key="cluster_name"
              :title="t('集群')" />
            <TableColumn
              v-if="accountType !== AccountTypes.MONGODB"
              col-key="db_module_name"
              :title="t('所属DB模块')" />
            <TableColumn
              col-key="operation"
              :title="t('操作')"
              :width="100">
              <template #default="{ rowIndex }">
                <BkButton
                  text
                  theme="primary"
                  @click="handleRemoveSelected(rowIndex)">
                  {{ t('删除') }}
                </BkButton>
              </template>
            </TableColumn>
          </PrimaryTable>
          <BkPagination
            v-bind="pagination"
            :layout="['total', 'limit', 'list']"
            :model-value="pagination.current"
            @change="handlePageChange"
            @limit-change="handleLimitChange" />
        </div>
      </Transition>
    </div>
  </BkFormItem>
  <ClusterSelector
    v-model:is-show="state.isShow"
    :cluster-types="clusterTypes"
    only-one-type
    :selected="selectedList"
    :tab-list-config="tabListConfig"
    @change="handleClusterChange" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getTendbSlaveClusterList } from '@services/source/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    accountType: AccountTypes;
    clusterTypes: string[];
    data: {
      cluster_name: string;
      cluster_type: string;
      db_module_name?: string;
      isMaster?: boolean;
      master_domain: string;
    }[];
  }

  type ResourceItem = Props['data'][number];

  type ClusterSelectorResult = Record<string, Props['data']>;

  interface Exposes {
    getClusterType(): ClusterTypes;
    init(clusterType: ClusterTypes, data: ResourceItem[]): void;
  }

  const props = defineProps<Props>();

  const targetInstances = defineModel<string[]>('modelValue', {
    default: () => [],
  });

  const { t } = useI18n();

  const formRef = ref();
  const rules = [
    {
      message: t('请添加目标集群'),
      trigger: 'change',
      validator: (value: string[]) => value.length > 0,
    },
  ];

  const tabListConfigMap = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      name: t('主从集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      name: t('单节点集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.TENDBCLUSTER]: {
      name: t('TendbCluster-主域名'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.TENDBHA]: {
      getResourceList: (params: ServiceParameters<typeof getTendbhaList>) => {
        const realParams = { ...params };
        realParams.master_domain = params.domain;
        delete realParams.domain;
        return getTendbhaList(realParams);
      },
      name: t('MySQL主从-主域名'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.TENDBSINGLE]: {
      name: t('MySQL单节点'),
      showPreviewResultTitle: true,
    },
    tendbclusterSlave: {
      getResourceList: (params: any) => {
        // eslint-disable-next-line no-param-reassign
        params.slave_domain = params.domain;
        // eslint-disable-next-line no-param-reassign
        delete params.domain;
        return getTendbSlaveClusterList(params);
      },
      name: t('TendbCluster-从域名'),
      showPreviewResultTitle: true,
    },
    tendbhaSlave: {
      getResourceList: (params: ServiceParameters<typeof getTendbhaSalveList>) => {
        const realParams = { ...params };
        realParams.slave_domain = realParams.domain;
        delete realParams.domain;
        return getTendbhaSalveList(realParams).then((data) => ({
          ...data,
          results: data.results.reduce<ServiceReturnType<typeof getTendbhaSalveList>['results']>((result, item) => {
            item.cluster_entry.forEach((entryItem) => {
              if (entryItem.role === 'slave_entry') {
                result.push(
                  Object.assign({}, item, {
                    master_domain: entryItem.entry,
                  }),
                );
              }
            });
            return result;
          }, []),
        }));
      },
      name: t('MySQL主从-从域名'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<string, TabConfig>;

  const state = reactive({
    clusterType: ClusterTypes.TENDBHA as string,
    isShow: false,
    selected: {
      [ClusterTypes.MONGO_REPLICA_SET]: [],
      [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
      [ClusterTypes.TENDBCLUSTER]: [],
      [ClusterTypes.TENDBHA]: [],
      [ClusterTypes.TENDBSINGLE]: [],
      tendbclusterSlave: [],
      tendbhaSlave: [],
    } as ClusterSelectorResult,
    tableData: [] as ResourceItem[],
  });

  const collapse = ref(true);

  const pagination = reactive({
    align: 'right' as const,
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
  });

  const operations = [
    {
      label: t('清除所有'),
      onClick: () => {
        state.tableData = [];
      },
    },
    {
      label: t('复制所有域名'),
      onClick: () => {
        const value = state.tableData.map((item) => item.master_domain);
        execCopy(value.join('\n'), t('复制成功，共n条', { n: value.length }));
      },
    },
  ];

  const renderData = computed(() => {
    const start = (pagination.current - 1) * pagination.limit;
    return state.tableData.slice(start, start + pagination.limit);
  });

  const tabListConfig = computed(() =>
    props.clusterTypes.reduce(
      (prevConfig, clusterTypeItem) => ({
        ...prevConfig,
        [clusterTypeItem]: tabListConfigMap[clusterTypeItem],
      }),
      {} as Record<string, TabConfig>,
    ),
  );

  const selectedList = computed(() => {
    const { clusterType, selected, tableData } = state;
    selected[clusterType] = tableData;
    return selected;
  });

  watchEffect(() => {
    pagination.count = state.tableData.length;
    if ((pagination.current - 1) * pagination.limit >= pagination.count) {
      pagination.current = 1;
    }
  });

  watch(
    () => props.data,
    () => {
      if (props.data.length > 0) {
        state.clusterType = props.data[0].cluster_type;
        nextTick(() => {
          updateTableData(props.data);
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowTargetCluster = () => {
    state.isShow = true;
  };

  const updateTableData = (data: ResourceItem[]) => {
    formRef.value.clearValidate();
    state.tableData = data;
    targetInstances.value = data.map((item) => item.master_domain);
  };

  const handleToggle = () => {
    collapse.value = !collapse.value;
  };

  const handlePageChange = (current: number) => {
    pagination.current = current;
  };

  const handleLimitChange = (limit: number) => {
    pagination.limit = limit;
    pagination.current = 1;
  };

  const handleClusterChange = (selected: ClusterSelectorResult) => {
    const list: ResourceItem[] = [];
    Object.keys(selected).forEach((key) => {
      if (selected[key].length > 0) {
        state.clusterType = key as ClusterTypes;
      }
      list.push(...selected[key]);
    });
    state.selected = selected;
    updateTableData(list);
  };

  const handleRemoveSelected = (index: number) => {
    state.tableData.splice(index, 1);
  };

  defineExpose<Exposes>({
    getClusterType() {
      let clusterType = state.clusterType as string;
      if (clusterType === 'tendbhaSlave') {
        clusterType = 'tendbha';
      } else if (clusterType === 'tendbclusterSlave') {
        clusterType = 'tendbcluster';
      }
      return clusterType as ClusterTypes;
    },
    init(clusterType: ClusterTypes, data: ResourceItem[]) {
      state.clusterType = clusterType;
      state.selected = {
        [clusterType]: data,
      };
      updateTableData(data);
    },
  });
</script>

<style lang="less" scoped>
  .target-cluster-table {
    font-weight: normal;
    color: @default-color;

    .target-cluster-table-header {
      display: flex;
      align-items: center;
      height: 42px;
      padding: 0 16px;
      font-size: @font-size-mini;
      cursor: pointer;
      background-color: @bg-dark-gray;
      justify-content: space-between;
    }

    .target-cluster-table-left {
      display: flex;
      align-items: center;
    }

    .target-cluster-table-icon {
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    .target-cluster-table-title {
      display: flex;
      align-items: center;
      padding-left: 4px;
    }

    .target-cluster-table-dropdown {
      font-size: 0;
      line-height: 20px;
    }

    .target-cluster-table-trigger {
      display: block;
      font-size: 20px;
      cursor: pointer;

      &:hover {
        background-color: @bg-disable;
        border-radius: 2px;
      }
    }

    .target-cluster-table-content {
      :deep(thead th) {
        background-color: #f5f7fa !important;
      }

      :deep(.bk-pagination-small-list) {
        order: 3;
        flex: 1;
        justify-content: flex-end;
      }

      :deep(.bk-pagination-limit-select) {
        .bk-input {
          border-color: #f0f1f5;
        }
      }

      :deep(.domain-column) {
        .master-icon {
          display: inline-block;
          width: 20px;
          height: 20px;
          line-height: 20px;
          color: #3a84ff;
          text-align: center;
          background: #f0f5ff;
          border-radius: 2px;
        }

        .slave-icon {
          .master-icon();

          color: #1cab88;
          background: #f2fff4;
        }
      }
    }

    &.target-cluster-table-expand {
      .target-cluster-table-icon {
        transform: rotate(0);
      }
    }
  }
</style>
