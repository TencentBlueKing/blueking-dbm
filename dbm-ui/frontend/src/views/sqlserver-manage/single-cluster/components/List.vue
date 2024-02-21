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
          class="ml-8"
          @click="handleShowAuthorize(selected)">
          {{ t('批量授权') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
        <DropdownExportExcel
          export-type="cluster"
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="sqlserver_single" />
      </div>
      <DbSearchSelect
        v-model="searchValues"
        class="header-select"
        :data="searchData"
        :placeholder="t('访问入口_集群名称_管控区域_实例_所属DB模块_创建人')"
        @change="handleFetchTableData" />
    </div>
    <div class="table-wrapper">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getSingleClusterList"
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
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.SQLSERVER_SINGLE" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';
  import {
    getSingleClusterList,
    getSqlServerInstanceList,
  } from '@services/source/sqlserverSingleCluster';
  import { createTicket } from '@services/source/ticket';

  import {
    type IPagination,
    useCopy,
    useDefaultPagination,
    useInfoWithIcon,
    useStretchLayout,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
    type TicketTypesStrings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import ExcelAuthorize from '@components/cluster-common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import RenderOperationTag from '@views/mysql/common/RenderOperationTag.vue';

  import {
    getSearchSelectorParams,
    messageWarn,
  } from '@utils';

  import type { SearchSelectValues } from '@types/bkui-vue';

  interface copyListType {
    ip: string,
    name: string,
    port: number,
    status: string,
    bk_instance_id: number,
  }

  const singleClusterData = defineModel<{ clusterId: number }>('singleClusterData');

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const copy = useCopy();

  const {
    t,
    locale,
  } = useI18n();

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
    handleOpenChange,
  } = useStretchLayout();

  const searchData = [
    {
      name: t('实例'),
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
  const selected = ref<SqlServerSingleClusterModel[]>([]);
  const searchValues = ref<SearchSelectValues>([]);
  const isAnomalies = ref(false);
  const pagination = ref<IPagination>(useDefaultPagination());
  const isShowExcelAuthorize = ref(false);

  /** 集群授权 */
  const authorizeShow = ref(false);

  const authorizeSelected = ref<{
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
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
      field: 'master_domain',
      fixed: 'left',
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <div class="domain">
          <RenderTextEllipsisOneLine
            onClick={ () => handleToDetails(data) }
            text={ data.master_domain }>
            <div class="cluster-tags">
              {
                data.operations.map(item => (
                  <RenderOperationTag
                    class="cluster-tag"
                    data={ item } />
                ))
              }
            </div>
            <div style="display: flex; align-items: center;">
              <db-icon
                type="copy"
                v-bk-tooltips={ t('复制主访问入口') }
                onClick={ () => copy(data.master_domain) } />
              <db-icon
                type="link"
                v-bk-tooltips={ t('新开tab打开') }
                onClick={ () => handleToDetails(data, true) }/>
              <div
                class="text-overflow"
                v-overflow-tips>
                 {
                   data.isNew && (
                     <span
                       class="glob-new-tag cluster-tag ml-4"
                       data-text="NEW" />
                   )
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
      field: 'bk_cloud_name',
    },
    {
      label: t('状态'),
      field: 'status',
      sort: true,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => {
        const {
          text,
          theme,
        } = data.dbStatusConfigureObj;
        return <DbStatus theme={ theme }>{ text }</DbStatus>;
      },
    },
    {
      label: t('实例'),
      field: 'instance_name',
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <RenderInstances
          data={ data.operations }
          dataSource={ getSqlServerInstanceList }
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
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <>
         {
          data.phase === 'online' ? (
           <>
            <OperationBtnStatusTips data={ data }>
             <bk-button
               text
               theme="primary"
               class="mr-8"
               onClick={ () => handleShowAuthorize([data]) }>
                { t('授权') }
             </bk-button>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips data={ data }>
             <bk-button
                text
                theme="primary"
                class="mr-8"
                onClick={ () => handleSwitchCluster(TicketTypes.SQLSERVER_SINGLE_DISABLE, data) }>
             { t('禁用') }
             </bk-button>
            </OperationBtnStatusTips>
           </>
          ) : (
           <>
            <OperationBtnStatusTips data={ data }>
              <bk-button
                text
                theme="primary"
                class="mr-8"
                onClick={ () => handleSwitchCluster(TicketTypes.SQLSERVER_SINGLE_ENABLE, data) }>
                 { t('启用') }
              </bk-button>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips data={ data }>
              <bk-button
                text
                theme="primary"
                class="mr-8">
                 { t('重置') }
              </bk-button>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips data={ data }>
              <bk-button
                text
                theme="primary"
                class="mr-8"
                onClick={ () => handleDeleteCluster(data) }>
                 { t('删除') }
              </bk-button>
            </OperationBtnStatusTips>
           </>
           )
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


  const { run: runCreateTicket } = useRequest(createTicket, { manual: true });

  const { run: runDeleteTicket } = useRequest(createTicket, {
    manual: true,
    onSuccess(res) {
      ticketMessage(res.id);
    },
  });

  /**
   * 集群启停
   */
  const handleSwitchCluster = (
    type: TicketTypesStrings,
    data: SqlServerSingleClusterModel,
  ) => {
    if (!type) return;

    const isOpen = type === TicketTypes.SQLSERVER_SINGLE_ENABLE;
    const title = isOpen ? t('确定启用该集群') : t('确定禁用该集群');
    useInfoWithIcon({
      type: 'warnning',
      title,
      content: () => (
        <div style="word-break: all;">
          {
            isOpen
              ? <p>{ t('集群【name】启用后将恢复访问', { name: data.cluster_name })}</p>
              : <p>{ t('集群【name】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { name: data.cluster_name }) }</p>
          }
        </div>
      ),
      onConfirm: () => {
        runCreateTicket({
          bk_biz_id: currentBizId,
          ticket_type: type,
          details: {
            cluster_ids: [data.id],
          },
        });
        return true;
      },
    });
  };

  /**
   * 删除集群
   */
  const handleDeleteCluster = (data: SqlServerSingleClusterModel) => {
    const { cluster_name: name } = data;
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定删除该集群'),
      confirmTxt: t('删除'),
      confirmTheme: 'danger',
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{ t('集群【name】被删除后_将进行以下操作', { name }) }</p>
          <p>{ t('1_删除xx集群', { name }) }</p>
          <p>{ t('2_删除xx实例数据_停止相关进程', { name }) }</p>
          <p>3. { t('回收主机') }</p>
        </div>
      ),
      onConfirm: () => {
        runDeleteTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.SQLSERVER_SINGLE_DESTROY,
          details: {
            cluster_ids: [data.id],
          },
        });
        return false;
      },
    });
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  const handleFetchTableData = () => {
    tableRef.value.fetchData(
      { ...getSearchSelectorParams(searchValues.value) },
      { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID },
    );
  };

  const handleCopy = (
    isInstance: boolean,
    tableData: SqlServerSingleClusterModel[],
  ) => {
    const AllCopyList = tableData
      .reduce((
        acc: copyListType[],
        item: SqlServerSingleClusterModel,
      ) => acc.concat(item.storages), []);
    if (AllCopyList.length) {
      copy(AllCopyList.map(item => `${item.ip}${isInstance ? `:${item.port}` : ''}`).join('\n'));
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
    const tableData = (tableRef.value.getData() as SqlServerSingleClusterModel[]).filter(item => item.status !== 'running');
    handleCopy(isInstance, tableData);
  };

  // 设置行样式
  const setRowClass = (row: SqlServerSingleClusterModel) => {
    const classStack = [];
    if (row.isNew) {
      classStack.push('is-new-row');
    }
    if (singleClusterData.value && row.id === singleClusterData.value.clusterId) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  const handleSelection = (
    data: SqlServerSingleClusterModel,
    list: SqlServerSingleClusterModel[],
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
  const handleToDetails = (
    data: SqlServerSingleClusterModel,
    isAllSpread: boolean = false,
  ) => {
    stretchLayoutSplitScreen();
    singleClusterData.value = { clusterId: data.id };
    if (isAllSpread) {
      handleOpenChange('left');
    }
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceSingleApply',
      query: {
        bizId: currentBizId,
        from: String(route.name),
      },
    });
  };
</script>
<style lang="less" scoped>
@import "@styles/mixins.less";

.sqlserver-single-cluster-list {
  height: 100%;
  padding: 24px 0;
  margin: 0 24px;
  overflow: hidden;

  .header-action {
    display: flex;
    flex-wrap: wrap;

    .header-select {
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

    .db-icon-copy,
    .db-icon-link {
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

    .db-icon-copy,
    .db-icon-link {
      display: inline-block !important;
    }
  }
}
</style>
