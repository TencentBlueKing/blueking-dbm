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
    <DBCollapseTable
      v-if="state.tableProps.data.length > 0"
      class="mt-16"
      :operations="state.operations"
      :table-props="{
        ...state.tableProps,
        columns: collapseTableColumns,
      }"
      :title="tabListConfigMap[state.clusterType].name" />
  </BkFormItem>
  <ClusterSelector
    v-model:is-show="state.isShow"
    :cluster-types="clusterTypes"
    only-one-type
    :selected="selectedList"
    :tab-list-config="tabListConfig"
    @change="handleClusterChange" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getTendbSlaveClusterList } from '@services/source/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';

  import { useCopy } from '@hooks';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';

  interface Props {
    accountType: AccountTypes;
    clusterTypes: string[];
    data: {
      master_domain: string;
      cluster_name: string;
      cluster_type: ClusterTypes;
      db_module_name?: string;
      isMaster?: boolean;
    }[];
  }

  type ResourceItem = Props['data'][number];

  type ClusterSelectorResult = Record<string, Props['data']>;

  interface Exposes {
    getClusterType(): ClusterTypes,
    init(clusterType: ClusterTypes, data: ResourceItem[]): void;
  }

  const props = defineProps<Props>();

  const targetInstances = defineModel<string[]>('modelValue', {
    default: () => [],
  });

  const { t } = useI18n();
  const copy = useCopy();

  const formRef = ref();
  const rules = [
    {
      trigger: 'change',
      message: t('请添加目标集群'),
      validator: (value: string[]) => value.length > 0,
    },
  ]

  const tabListConfigMap = {
    tendbhaSlave: {
      name: t('MySQL主从-从域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: ServiceParameters<typeof getTendbhaSalveList>) => {
        const realParams = { ...params }
        realParams.slave_domain = realParams.domain;
        delete realParams.domain;
        return getTendbhaSalveList(realParams).then(data => ({
          ...data,
          results: data.results.reduce<ServiceReturnType<typeof getTendbhaSalveList>['results']>((result, item) => {
            item.cluster_entry.forEach(entryItem => {
              if (entryItem.role === 'slave_entry') {
                result.push(Object.assign({}, item, {
                  master_domain: entryItem.entry
                }))
              }
            })
            return result
          }, [])
        }))
      }
    },
    [ClusterTypes.TENDBCLUSTER]: {
      name: t('TendbCluster-主域名'),
      showPreviewResultTitle: true,
    },
    tendbclusterSlave: {
      name: t('TendbCluster-从域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: any) => {
        params.slave_domain = params.domain;
        delete params.domain;
        return getTendbSlaveClusterList(params)
      }
    },
    [ClusterTypes.TENDBHA]: {
      name: t('MySQL主从-主域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: ServiceParameters<typeof getTendbhaList>) => {
        const realParams = { ...params }
        realParams.master_domain = params.domain;
        delete realParams.domain;
        return getTendbhaList(realParams)
      }
    },
    [ClusterTypes.TENDBSINGLE]: {
      name: t('MySQL单节点'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      name: t('单节点集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      name: t('主从集群'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<string, TabConfig>;

  const state = reactive({
    clusterType: ClusterTypes.TENDBHA,
    selected: {
      [ClusterTypes.TENDBHA]: [],
      [ClusterTypes.TENDBSINGLE]: [],
      tendbhaSlave: [],
      [ClusterTypes.TENDBCLUSTER]: [],
      tendbclusterSlave: [],
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
      [ClusterTypes.MONGO_REPLICA_SET]: [],
      [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    } as ClusterSelectorResult,
    isShow: false,
    tableProps: {
      data: [] as ResourceItem[],
      pagination: {
        small: true,
        count: 0,
      },
    },
    operations: [
      {
        label: t('清除所有'),
        onClick: () => {
          state.tableProps.data = [];
        },
      },
      {
        label: t('复制所有域名'),
        onClick: () => {
          const value = state.tableProps.data.map((item) => item.master_domain).join('\n');
          copy(value);
        },
      },
    ],
  });

  const tabListConfig = computed(() => props.clusterTypes.reduce((prevConfig, clusterTypeItem) => ({
    ...prevConfig,
    [clusterTypeItem]: tabListConfigMap[clusterTypeItem],
  }), {} as Record<string, TabConfig>));

  const collapseTableColumns = computed(() => {
    const columns = [
      {
        label: t('域名'),
        field: 'master_domain',
        render: ({ data }: { data: ResourceItem }) => (
          data.isMaster !== undefined
            ? <div class="domain-column">
              {data.isMaster
                ? <span class="master-icon">{t('主')}</span>
                : <span class="slave-icon">{t('从')}</span>}
              <span class="ml-6">{data.master_domain}</span>
            </div>
            : <span>{data.master_domain}</span>
        ),
      },
      {
        label: t('集群'),
        field: 'cluster_name',
      },
      {
        label: t('操作'),
        field: 'operation',
        width: 100,
        render: ({ index }: { index: number }) => (
          <bk-button
            text
            theme="primary"
            onClick={() => handleRemoveSelected(index)}>
            {t('删除')}
          </bk-button>
        ),
      },
    ];

    if (props.accountType !== AccountTypes.MONGODB) {
      columns.splice(2, 0, {
        label: t('所属DB模块'),
        field: 'db_module_name',
      });
    }

    return columns;
  });

  const selectedList = computed(() => {
    const {
      clusterType,
      selected,
      tableProps,
    } = state;
    selected[clusterType] = tableProps.data;
    return selected;
  });

  watch(
    () => props.data,
    () => {
      if (props.data.length > 0) {
        state.clusterType = props.data[0].cluster_type;
        nextTick(() => {
          updateTableData(props.data);
        })
      }
    },
    {
      immediate: true,
    }
  );

  const handleShowTargetCluster = () => {
    state.isShow = true;
  };

  const updateTableData = (data: ResourceItem[]) => {
    formRef.value.clearValidate();
    state.tableProps.data = data;
    state.tableProps.pagination.count = data.length;
    targetInstances.value = data.map(item => item.master_domain);
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
    state.tableProps.data.splice(index, 1);
    state.tableProps.pagination.count = state.tableProps.pagination.count - 1;
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
    }
  });
</script>
