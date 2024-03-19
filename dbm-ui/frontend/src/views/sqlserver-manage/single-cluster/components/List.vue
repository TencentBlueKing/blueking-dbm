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
          @hide="() => (isCopyDropdown = false)"
          @show="() => (isCopyDropdown = true)">
          <BkButton
            class="dropdown-button"
            :class="{ active: isCopyDropdown }">
            {{ t('复制') }}
            <DbIcon type="up-big dropdown-button-icon" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem>
                <BkButton
                  :disabled="tableDataList.length === 0"
                  text
                  @click="handleCopy(tableDataList)">
                  {{ t('所有集群 IP') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="selected.length === 0"
                  text
                  @click="handleCopy(selected)">
                  {{ t('已选集群 IP') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="abnormalDataList.length === 0"
                  text
                  @click="handleCopy(abnormalDataList)">
                  {{ t('异常集群 IP') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="tableDataList.length === 0"
                  text
                  @click="handleCopy(tableDataList, true)">
                  {{ t('所有集群实例') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="selected.length === 0"
                  text
                  @click="handleCopy(selected, true)">
                  {{ t('已选集群实例') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="abnormalDataList.length === 0"
                  text
                  @click="handleCopy(abnormalDataList, true)">
                  {{ t('异常集群实例') }}
                </BkButton>
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择集群'),
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasSelected"
            @click="handleShowAuthorize(selected)">
            {{ t('批量授权') }}
          </BkButton>
        </span>
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
        :data="searchSelectData"
        :placeholder="t('域名_IP_模块')"
        @change="handleFetchTableData" />
    </div>
    <div class="table-wrapper">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getSingleClusterList"
        :row-class="setRowClass"
        selectable
        :settings="settings"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeShow"
    :account-type="AccountTypes.SQLSERVER"
    :cluster-types="[ClusterTypes.SQLSERVER_SINGLE]"
    :selected="authorizeSelected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
    :ticket-type="TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES"/>
  <ClusterReset
    v-if="currentData"
    v-model:is-show="isShowClusterReset"
    :data="currentData"></ClusterReset>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';
  import { getModules } from '@services/source/cmdb';
  import {
    getSingleClusterList,
    getSqlServerInstanceList,
  } from '@services/source/sqlserverSingleCluster';
  import { createTicket } from '@services/source/ticket';

  import {
    useCopy,
    useInfoWithIcon,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import ExcelAuthorize from '@components/cluster-common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import DbTable from '@components/db-table/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterReset from '@views/sqlserver-manage/components/cluster-reset/Index.vue'

  import { getSearchSelectorParams } from '@utils';

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

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isCopyDropdown = ref(false);
  const selected = ref<SqlServerSingleClusterModel[]>([]);
  const searchValues = ref([]);
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false)
  const currentData = ref<SqlServerSingleClusterModel>()

  /** 集群授权 */
  const authorizeShow = ref(false);

  const authorizeSelected = ref<{
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]>([]);

  const tableDataList = computed(() => tableRef.value!.getData<SqlServerSingleClusterModel>());
  const abnormalDataList = computed(() => tableDataList.value.filter(dataItem => dataItem.isAbnormal));
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isCN = computed(() => locale.value === 'zh-cn');

  const searchSelectData = computed(() => [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('访问入口'),
      id: 'domain',
    },
    {
      name: 'IP',
      id: 'ip',
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('模块'),
      id: 'db_module_id',
      children: (moduleList.value || []).map(moduleItem => ({
        id: moduleItem.db_module_id,
        name: moduleItem.name,
      })),
    },
  ]);

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 150 : 200;
    }
    return 100;
  });

  const columns = [
    {
      label: t('访问入口'),
      field: 'master_domain',
      fixed: 'left',
      width: 200,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <bk-button
                text
                theme="primary"
                onClick={() => handleToDetails(data)}>
                {data.master_domain}
              </bk-button>
            ),
            append: () => (
              <>
                <div class="cluster-tags">
                  {
                    data.operationTagTips.map(item => (
                      <RenderOperationTag
                        class="cluster-tag"
                        data={item} />
                    ))
                  }
                </div>
                <div style="display: flex; align-items: center;">
                  <db-icon
                    type="copy"
                    v-bk-tooltips={ t('复制主访问入口') }
                    onClick={ () => copy(data.master_domain) } />
                  {/* <db-icon
                    type="link"
                    v-bk-tooltips={ t('新开tab打开') }
                    onClick={ () => handleToDetails(data, true) }/> */}
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
              </>
            ),
          }}
        </TextOverflowLayout>
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
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('实例'),
      field: 'storages',
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <RenderInstances
          data={ data.storages }
          dataSource={ getSqlServerInstanceList }
          title={ t('【inst】实例预览', { inst: data.bk_cloud_name }) }
          role="storages"
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
    },
    {
      label: t('创建时间'),
      field: 'create_time',
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: 'right',
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <>
          {
            data.isOnline ? (
              <>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    onClick={ () => handleShowAuthorize([data]) }>
                    { t('授权') }
                  </bk-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    class="ml-16"
                    onClick={ () => handleSwitchCluster(TicketTypes.SQLSERVER_DISABLE, data) }>
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
                    onClick={ () => handleSwitchCluster(TicketTypes.SQLSERVER_ENABLE, data) }>
                    { t('启用') }
                  </bk-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    class="ml-16"
                    onClick={() => handleResetCluster(data)}>
                    { t('重置') }
                  </bk-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    class="ml-16"
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

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field ,
      disabled: ['master_domain'].includes(item.field as string),
    })),
    checked: columns.map(item => item.field).filter(key => !!key && key !== 'id'),
    showLineHeight: false,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.SQLSERVER_SINGLE_TABLE_SETTINGS, defaultSettings);

  const { data: moduleList } = useRequest(getModules, {
    defaultParams: [{
      cluster_type: ClusterTypes.SQLSERVER_SINGLE,
      bk_biz_id: currentBizId,
    }]
  });

  const { run: createTicketRun } = useRequest(createTicket, {
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

    const isOpen = type === TicketTypes.SQLSERVER_ENABLE;
    useInfoWithIcon({
      type: 'warnning',
      title: isOpen ? t('确定启用该集群？') : t('确定禁用该集群？'),
      content: () => (
        <div style="word-break: all;">
          <p style="color: #313238">{t('集群')} ：{data.cluster_name}</p>
          {
            isOpen
              ? <p>{ t('启用后将恢复访问')}</p>
              : <p>{ t('被禁用后将无法访问，如需恢复访问，可以再次「启用」')}</p>
          }
        </div>
      ),
      confirmTxt: isOpen ? t('启用') : t('禁用'),
      onConfirm: () => {
        createTicketRun({
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
        createTicketRun({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.SQLSERVER_DESTROY,
          details: {
            cluster_ids: [data.id],
          },
        });
        return false;
      },
    });
  };

  const handleResetCluster = (data: SqlServerSingleClusterModel) => {
    currentData.value = data
    isShowClusterReset.value = true
  }

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  const handleFetchTableData = () => {
    tableRef.value!.fetchData(
      { ...getSearchSelectorParams(searchValues.value) },
      { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID },
    );
  };

  const handleCopy = (dataList: SqlServerSingleClusterModel[], isInstance = false) => {
    const list = dataList.reduce((prevList, tableItem) => {
      const storageList = tableItem.storages.map(storageItem => (isInstance ? `${storageItem.ip}:${storageItem.port}` : `${storageItem.ip}`));
      return [...prevList, ...storageList];
    }, [] as string[]);
    copy(list.join('\n'));
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

  const handleSelection = (key: number[], list: Record<number, SqlServerSingleClusterModel>[]) => {
    selected.value = list as unknown as SqlServerSingleClusterModel[];
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
  @import '@styles/mixins.less';

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
