<template>
  <div class="sqlserver-single-cluster-list">
    <div class="header-action">
      <div class="mb-16">
        <BkButton
          theme="primary"
          @click="handleApply">
          {{ t('实例申请') }}
        </BkButton>
        <BkDropdown
          class="ml-8"
          @hide="() => isCopyDropdown = false"
          @show="() => isCopyDropdown = true">
          <BkButton
            class="dropdown-button"
            :class="{ 'active': isCopyDropdown }">
            {{ t('复制') }}
            <DbIcon type="up-big dropdown-button-icon" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleCopyAll()">
                {{ t('所有集群 IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopySelected()">
                {{ t('已选集群 IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAbnormal()">
                {{ t('异常集群 IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAll(true)">
                {{ t('所有集群实例') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopySelected(true)">
                {{ t('已选集群实例') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAbnormal(true)">
                {{ t('异常集群实例') }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
        <BkButton
          class="ml-8">
          {{ t('批量授权') }}
        </BkButton>
        <BkButton
          class="ml-8">
          {{ t('导入授权') }}
        </BkButton>
        <DropdownExportExcel
          export-type="cluster"
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="sqlserversingle" />
      </div>
      <DbSearchSelect
        v-model="searchValues"
        class="header-select"
        :data="searchData"
        :placeholder="t('访问入口_集群名称_管控区域_实例_所属DB模块_创建人')"
        @change="handleFetchTableData" />
    </div>
    <div
      class="table-wrapper">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data="data"
        :is-anomalies="isAnomalies"
        :pagination="renderPagination"
        :pagination-extra="{ small: false }"
        :row-class="setRowClass"
        selectable
        @selection="handleSelection" />
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeShow"
    :cluster-type="ClusterTypes.SQLSERVER_HA"
    :selected="authorizeSelected"
    @success="handleClearSelected" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import SqlServerClusterListModel from '@services/model/sqlserver/sqlserver-cluster-list';
  import { getSingleClusterList } from '@services/source/sqlserverSingleCluster';

  import {
    type IPagination,
    useCopy,
    useDefaultPagination,
    useStretchLayout,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import {
    getSearchSelectorParams,
    messageWarn,
  } from '@utils';

  import type { SearchSelectValues } from '@types/bkui-vue';

  interface copyListType{
    ip: string,
    name: string,
    port: number,
    status: string,
    bk_instance_id: number,
  }

  const singleClusterData = defineModel<{
    clusterId: number,
  }>('singleClusterData');

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();

  const {
    t,
    locale,
  } = useI18n();

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const searchData = [
    {
      name: '实例',
      id: 'instance_address',
    },
    {
      name: t('所属集群'),
      id: 'cluster_id',
    },
    {
      name: t('主域名'),
      id: 'master_domain',
    },
  ];

  const tableRef = ref();
  const isCopyDropdown = ref(false);
  const selected = ref<SqlServerClusterListModel[]>([]);
  const searchValues = ref<SearchSelectValues>([]);
  const isAnomalies = ref(false);
  const pagination = ref<IPagination>(useDefaultPagination());

  /** 集群授权 */
  const authorizeShow = ref(false);

  const authorizeSelected = ref<{
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.bk_host_id));
  const isCN = computed(() => locale.value === 'zh-cn');

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 270 : 420;
    }
    return 100;
  });

  const columns = [
    {
      label: t('访问入口'),
      field: 'master_enter',
      fixed: 'left',
      render: ({ data }: { data: SqlServerClusterListModel }) => (
        <div class = "domain">
         <RenderTextEllipsisOneLine
           onClick = { () => handleToDetails(data) }
           text = { data.master_enter }>
            <div style = "display: flex; align-items: center;">
              <db-icon
                type = "copy"
                v-bk-tooltips={ t('复制主访问入口') }
                onClick = { () => copy(data.master_enter) }/>
              <db-icon
                type = "link"
                v-bk-tooltips = { t('新开tab打开') }/>
              <div class = "text-overflow" v-overflow-tips>
                {
                  data.isNew
                  && <span
                       class = "glob-new-tag cluster-tag ml-4"
                       data-text = "NEW"/>
                }
              </div>
            </div>
         </RenderTextEllipsisOneLine>
        </div>
      ),
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
    },
    {
      label: t('管控区域'),
      field: 'control_area',
    },
    {
      label: t('状态'),
      field: 'status',
      sort: true,
      render: ({ data }: { data: SqlServerClusterListModel }) => {
        const { text, theme } = data.dbStatusConfigureObj;
        return <DbStatus theme={ theme }>{ text }</DbStatus>;
      },
    },
    {
      label: t('实例'),
      field: 'instance_name',
      render: ({ data }: { data: SqlServerClusterListModel }) => (
        <RenderInstances
          data={ data.proxies }
          title={ t('【inst】实例预览', { inst: data.bk_cloud_name }) }
          role="proxy"
          clusterId={ data.id }
        />
      ),
    },
    {
      label: t('所属DB模块'),
      field: 'belong_DB_module',
    },
    {
      label: t('创建人'),
      field: 'create_user',
      sort: true,
    },
    {
      label: t('创建时间'),
      field: 'create_time',
      sort: true,
    },
    {
      label: t('操作'),
      field: 'operation',
      width: tableOperationWidth.value,
      fixed: 'right',
      render: ({ data }: { data: SqlServerClusterListModel }) => (
       <>
        <OperationStatusTips class="mr8">
          <bk-button
            text
            theme="primary"
            class="mr-8"
            onClick={ () => handleShowAuthorize([data]) }>
             { t('授权') }
          </bk-button>
        </OperationStatusTips>
          {
           <>
            <OperationStatusTips class="mr8">
              <bk-button
                text
                theme="primary"
                class="mr-8">
                 { t('禁用') }
              </bk-button>
            </OperationStatusTips>
            <OperationStatusTips class="mr8">
              <bk-button
                text
                theme="primary"
                class="mr-8">
                 { t('启用') }
              </bk-button>
            </OperationStatusTips>
            <OperationStatusTips class="mr8">
              <bk-button
                text
                theme="primary"
                class="mr-8">
                 { t('重置') }
              </bk-button>
            </OperationStatusTips>
            <OperationStatusTips class="mr8">
              <bk-button
                text
                theme="primary"
                class="mr-8">
                 { t('删除') }
              </bk-button>
            </OperationStatusTips>
           </>
          }
        </>
       ),
    },
  ];

  const renderPagination = computed(() => {
    if (pagination.value.count < 10) {
      return false;
    }
    if (!isStretchLayoutOpen.value) {
      return { ...pagination.value };
    }
    return {
      ...pagination.value,
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  const { data } =  useRequest(getSingleClusterList);

  const handleFetchTableData = () => {
    tableRef.value.fetchData({
      ...getSearchSelectorParams(searchValues.value),
    }, {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };

  const handleCopy = (
    isInstance:boolean,
    tableData:SqlServerClusterListModel[],
  ) => {
    const AllCopyList = tableData
      .reduce((acc: copyListType[], item:SqlServerClusterListModel) => acc.concat(item.proxies), []);
    if (AllCopyList?.length) {
      copy(AllCopyList.map((item: copyListType) => `${item.ip}${isInstance ? `:${item.port}` : ''}`).join('\n'));
    } else {
      messageWarn(isInstance ? t('没有可复制实例') : t('没有可复制IP'));
    }
  };

  const handleCopyAll = (isInstance = false) => {
    const tableData = tableRef.value.getData();
    handleCopy(isInstance, tableData);
  };

  const handleCopySelected = (isInstance = false) => {
    const tableData = selected.value;
    if (tableData.length) {
      handleCopy(isInstance, tableData);
    } else {
      messageWarn(t('请先勾选数据'));
    }
  };

  const handleCopyAbnormal = (isInstance = false) => {
    const tableData  = (tableRef.value.getData() as SqlServerClusterListModel[]).filter(item => item.status !== 'running');
    handleCopy(isInstance, tableData);
  };

  // 设置行样式
  const setRowClass = (row: SqlServerClusterListModel) => {
    const classStack = [];
    if (row.isNew) {
      classStack.push('is-new-row');
    }
    if (
      singleClusterData.value && row.clusterId === singleClusterData.value.clusterId
    ) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  const handleSelection = (
    data: SqlServerClusterListModel,
    list: SqlServerClusterListModel[],
  ) => {
    selected.value = list;
  };

  const handleClearSelected = () => {
    selected.value = [];
    authorizeSelected.value = [];
  };

  const handleShowAuthorize = (selected: {
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]) => {
    authorizeShow.value = true;
    authorizeSelected.value = selected;
  };

  /**
   * 查看详情
   */
  const handleToDetails = (data: SqlServerClusterListModel) => {
    stretchLayoutSplitScreen();
    singleClusterData.value = {
      clusterId: data.clusterId,
    };
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceSingleApply',
      query: {
        bizId: globalBizsStore.currentBizId,
        from: String(route.name),
      },
    });
  };
</script>
<style lang="less" scoped>
@import "@styles/mixins.less";

.sqlserver-single-cluster-list{
  height: 100%;
  padding: 24px 0;
  margin: 0 24px;
  overflow: hidden;

  .header-action {
    display: flex;
    flex-wrap: wrap;

    .header-select{
      flex: 1;
      max-width: 320px;
      min-width: 320px;
      margin-left: auto;
    }
  }

  :deep(.cell) {
    line-height: normal !important;

    .domain {
      display: flex;
      align-items: center;
    }

    .db-icon-copy, .db-icon-link {
      display: none;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }

    .operations-more {
      .db-icon-more {
        display: block;
        font-size: @font-size-normal;
        font-weight: bold;
        color: @default-color;
        cursor: pointer;

        &:hover {
          background-color: @bg-disable;
          border-radius: 2px;
        }
      }
    }
  }

  :deep(tr:hover) {
    .db-icon-copy, .db-icon-link {
      display: inline-block !important;
    }
  }
}
</style>
