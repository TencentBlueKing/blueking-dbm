<template>
  <div class="sqlserver-ha-cluster-list">
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
          type="sqlserver_ha" />
      </div>
      <DbSearchSelect
        v-model="searchValues"
        class="header-select mb-16"
        :data="searchSelectData"
        :placeholder="t('域名_IP_模块')"
        @change="handleFetchTableData" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getHaClusterList"
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
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :selected="authorizeSelected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.SQLSERVER_HA"
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

  import SqlServerHaClusterModel from '@services/model/sqlserver/sqlserver-ha-cluster';
  import { getModules } from '@services/source/cmdb';
  import {
    getHaClusterList,
    getSqlServerInstanceList,
  } from '@services/source/sqlserveHaCluster';
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

  const haClusterData = defineModel<{
    clusterId: number,
  }>('haClusterData');

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const {
    t,
    locale,
  } = useI18n();

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
    handleOpenChange,
  } = useStretchLayout();

  const copy = useCopy();

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isCopyDropdown = ref(false);
  const selected = ref<SqlServerHaClusterModel[]>([]);
  const searchValues = ref([]);
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false)
  const currentData = ref<SqlServerHaClusterModel>()

  /** 集群授权 */
  const authorizeShow = ref(false);

  const authorizeSelected = ref<{
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]>([]);

  const tableDataList = computed(() => tableRef.value!.getData<SqlServerHaClusterModel>());
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

  const { run: createTicketRun } = useRequest(createTicket, {
    manual: true,
    onSuccess(res) {
      ticketMessage(res.id);
    },
  });

  const columns = [
    {
      label: t('主访问入口'),
      field: 'master_domain',
      fixed: 'left',
      width: 200,
      render: ({ data }: { data: SqlServerHaClusterModel }) => (
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
                    onClick={ () => copy(data.master_domain) }/>
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
                            data-text="NEW"/>
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
      label: t('从访问入口'),
      fixed: 'left',
      field: 'slave_domain',
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
      render: ({ data }: { data: SqlServerHaClusterModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: 'Master',
      field: 'Master',
      width: 180,
      render: ({ data }: { data: SqlServerHaClusterModel }) => (
        <RenderInstances
          data={ data.masters }
          title={ t('【inst】实例预览', { inst: data.bk_cloud_name, title: 'Master' }) }
          role="proxy"
          clusterId={ data.id }
          dataSource={ getSqlServerInstanceList } />
      ),
    },
    {
      label: 'Slave',
      field: 'Slave',
      width: 180,
      render: ({ data }: { data: SqlServerHaClusterModel }) => (
        <RenderInstances
          data={ data.slaves }
          title={ t('【inst】实例预览', { inst: data.bk_cloud_name, title: 'Slaves' }) }
          role="proxy"
          clusterId={ data.id }
          dataSource={ getSqlServerInstanceList } />
    ),
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_name',
    },
    {
      label: t('创建人'),
      field: 'creator',
    },
    {
      label: t('创建时间'),
      field: 'create_at',
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: 'right',
      render: ({ data }: { data: SqlServerHaClusterModel }) => (
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
                    onClick={() => handleSwitchCluster(TicketTypes.SQLSERVER_DISABLE, data)}>
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
                    onClick={() => handleDeleteCluster(data)}>
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
      cluster_type: ClusterTypes.SQLSERVER_HA,
      bk_biz_id: currentBizId,
    }]
  });

  const handleFetchTableData = () => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValues.value),
    }, {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };

  const handleCopy = (dataList: SqlServerHaClusterModel[], isInstance = false) => {
    const list = dataList.reduce((prevList, tableItem) => {
      const masterList = tableItem.masters.map(masterItem => (isInstance ? `${masterItem.ip}:${masterItem.port}` : `${masterItem.ip}`));
      const slaveList = tableItem.slaves.map(slavesItem => (isInstance ? `${slavesItem.ip}:${slavesItem.port}` : `${slavesItem.ip}`));
      return [...prevList, ...masterList, ...slaveList];
    }, [] as string[]);
    copy(list.join('\n'));
  };

  /**
   * 集群启停
   */
  const handleSwitchCluster = (
    type: TicketTypesStrings,
    data: SqlServerHaClusterModel,
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
  const handleDeleteCluster = (data: SqlServerHaClusterModel) => {
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

  const handleResetCluster = (data: SqlServerHaClusterModel) => {
    currentData.value = data
    isShowClusterReset.value = true
  }

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  // 设置行样式
  const setRowClass = (row: SqlServerHaClusterModel) => {
    const classStack = [];
    if (row.isNew) {
      classStack.push('is-new-row');
    }
    if (haClusterData.value && row.id === haClusterData.value.clusterId) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  /**
   * 查看详情
   */
  const handleToDetails = (
    data: SqlServerHaClusterModel,
    isAllSpread = false,
  ) => {
    stretchLayoutSplitScreen();
    haClusterData.value = {
      clusterId: data.id,
    };
    if (isAllSpread) {
      handleOpenChange('left');
    }
  };

  const handleSelection = (key: number[], list: Record<number, SqlServerHaClusterModel>[]) => {
    selected.value = list as unknown as SqlServerHaClusterModel[];
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
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceHaApply',
      query: {
        bizId: currentBizId,
        from: String(route.name),
      },
    });
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .sqlserver-ha-cluster-list {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .cluster-tags {
      display: flex;
      margin-left: 4px;
      align-items: center;
      flex-wrap: wrap;
    }

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
