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
  <div class="mysql-ha-cluster-list">
    <div class="operation-box">
      <div class="mb-16">
        <AuthButton
          action-id="mysql_apply"
          theme="primary"
          @click="handleApply">
          {{ t('实例申请') }}
        </AuthButton>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择集群')
          }"
          class="inline-block">
          <AuthButton
            action-id="mysql_authorize"
            class="ml-8"
            :disabled="!hasSelected"
            @click="() => handleShowCreateSubscribeRuleSlider()">
            {{ t('批量订阅') }}
          </AuthButton>
        </span>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择集群')
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasSelected"
            @click="handleShowAuthorize(state.selected)">
            {{ t('批量授权') }}
          </BkButton>
        </span>
        <AuthButton
          action-id="mysql_excel_authorize"
          class="ml-8"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </AuthButton>
        <DropdownExportExcel
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="tendbha" />
      </div>
      <DbSearchSelect
        v-model="state.filters"
        class="mb-16"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :placeholder="t('域名_IP_模块')"
        style="width: 320px;"
        unique-select
        @change="handleSearch" />
    </div>
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': isStretchLayoutOpen}">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getTendbhaList"
        releate-url-query
        :row-class="setRowClass"
        selectable
        :settings="settings"
        @clear-search="handleClearSearch"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeState.isShow"
    :cluster-type="ClusterTypes.TENDBHA"
    :selected="authorizeState.selected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.TENDBHA" />
  <EditEntryConfig
    :id="clusterId"
    v-model:is-show="showEditEntryConfig"
    :get-detail-info="getTendbhaDetail" />
  <CreateSubscribeRuleSlider
    v-model="showCreateSubscribeRuleSlider"
    :selected-clusters="selectedClusterList"
    show-tab-panel />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import type { MySQLFunctions } from '@services/model/function-controller/functionController';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getModules } from '@services/source/cmdb';
  import {
    getTendbhaDetail,
    getTendbhaInstanceList,
    getTendbhaList,
  } from '@services/source/tendbha';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';
  import type {
    SearchFilterItem,
  } from '@services/types';

  import {
    useCopy,
    useInfoWithIcon,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import {
    useFunController,
    useGlobalBizs,
  } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import ExcelAuthorize from '@components/cluster-common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import EditEntryConfig from '@components/cluster-entry-config/Index.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import CreateSubscribeRuleSlider from '@views/mysql/dumper/components/create-rule/Index.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  import type { SearchSelectItem } from '@/types/bkui-vue';

  interface ColumnData {
    cell: string,
    data: TendbhaModel
  }

  interface State {
    selected: Array<TendbhaModel>,
    filters: Array<any>,
    dbModuleList: Array<SearchFilterItem>,
  }

  const clusterId = defineModel<number>('clusterId');

  // 设置行样式
  const setRowClass = (row: TendbhaModel) => {
    const classList = [row.isOffline ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const funControllerStore = useFunController();
  const copy = useCopy();
  const ticketMessage = useTicketMessage();
  const { t, locale } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();


  const tableRef = ref();
  const isShowExcelAuthorize = ref(false);
  const isInit = ref(false);
  const showEditEntryConfig = ref(false);
  const showCreateSubscribeRuleSlider = ref(false);
  const selectedClusterList = ref<ColumnData['data'][]>([]);

  const state = reactive<State>({
    selected: [],
    filters: [],
    dbModuleList: [],
  });

  /** 集群授权 */
  const authorizeState = reactive({
    isShow: false,
    selected: [] as TendbhaModel[],
  });

  const isCN = computed(() => locale.value === 'zh-cn');
  const hasSelected = computed(() => state.selected.length > 0);
  const selectedIds = computed(() => state.selected.map(item => item.id));
  const searchSelectData = computed(() => [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('主访问入口'),
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
      children: [],
    },
  ]);
  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 200 : 280;
    }
    return 60;
  });

  const searchIp = computed<string[]>(() => {
    const ipObj = state.filters.find(item => item.id === 'ip');
    if (ipObj) {
      return [ipObj.values[0].id];
    }
    return [];
  });
  const isShowDumperEntry = computed(() => {
    const currentKey = `dumper_biz_${globalBizsStore.currentBizId}` as MySQLFunctions;
    return funControllerStore.funControllerData.mysql.children[currentKey];
  });

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('主访问入口'),
      field: 'master_domain',
      fixed: 'left',
      width: 200,
      minWidth: 200,
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="mysql_view"
                resource={data.id}
                permission={data.permission.mysql_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.masterDomainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                <db-icon
                  type="copy"
                  v-bk-tooltips={t('复制主访问入口')}
                  onClick={() => copy(data.masterDomainDisplayName)} />
                <auth-button
                  v-bk-tooltips={t('修改入口配置')}
                  action-id="access_entry_edit"
                  resource="mysql"
                  permission={data.permission.access_entry_edit}
                  text
                  theme="primary"
                  onClick={() => handleOpenEntryConfig(data)}>
                  <db-icon type="edit" />
                </auth-button>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 200,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => (
        <TextOverflowLayout>
          {{
            default: () => data.cluster_name,
            append: () => (
              <>
                {
                  data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
                }
                {
                  data.isOffline && !data.isStarting && (
                    <db-icon
                      svg
                      type="yijinyong"
                      class="cluster-tag ml-4"
                      style="width: 38px; height: 16px;" />
                  )
                }
                {
                  isRecentDays(data.create_at, 24 * 3) && (
                    <span
                      class="glob-new-tag cluster-tag ml-4"
                      data-text="NEW" />
                  )
                }
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  type="copy"
                  onClick={() => copy(data.cluster_name)} />
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      width: 90,
    },
    {
      label: t('状态'),
      field: 'status',
      width: 90,
      render: ({ data }: ColumnData) => {
        const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('从访问入口'),
      field: 'slave_domain',
      minWidth: 200,
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => (
        <div class="domain">
          <span
            class="text-overflow"
            v-overflow-tips>
            {data.slaveDomainDisplayName || '--'}
          </span>
          <db-icon
            v-bk-tooltips={t('复制从访问入口')}
            type="copy"
            onClick={() => copy(data.slaveDomainDisplayName)} />
          <auth-button
            v-bk-tooltips={t('修改入口配置')}
            action-id="access_entry_edit"
            resource="mysql"
            permission={data.permission.access_entry_edit}
            text
            theme="primary"
            onClick={() => handleOpenEntryConfig(data)}>
            <db-icon type="edit" />
          </auth-button>
        </div>
      ),
    },
    {
      label: 'Proxy',
      field: 'proxies',
      minWidth: 180,
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => (
        <RenderInstances
          highlightIps={searchIp.value}
          data={data.proxies || []}
          title={t('【inst】实例预览', { inst: data.master_domain, title: 'Proxy' })}
          role="proxy"
          clusterId={data.id}
          dataSource={getTendbhaInstanceList}
        />
      ),
    },
    {
      label: 'Master',
      field: 'masters',
      minWidth: 180,
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => (
        <RenderInstances
          highlightIps={searchIp.value}
          data={data.masters}
          title={t('【inst】实例预览', { inst: data.master_domain, title: 'Master' })}
          role="proxy"
          clusterId={data.id}
          dataSource={getTendbhaInstanceList}
        />
      ),
    },
    {
      label: 'Slave',
      field: 'slaves',
      minWidth: 180,
      width: 200,
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => (
        <RenderInstances
          highlightIps={searchIp.value}
          data={data.slaves || []}
          title={t('【inst】实例预览', { inst: data.master_domain, title: 'Slave' })}
          role="slave"
          clusterId={data.id}
          dataSource={getTendbhaInstanceList}
        />
      ),
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_name',
      width: 140,
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('创建时间'),
      field: 'create_at',
      width: 160,
      render: ({ data }: ColumnData) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: ColumnData) => (
          <>
            <auth-button
              text
              theme="primary"
              class="mr-8"
              actionId="mysql_authorize"
              permission={data.permission.mysql_authorize}
              resource={data.id}
              onClick={() => handleShowAuthorize([data])}>
              { t('授权') }
            </auth-button>
            {isShowDumperEntry.value && (
              <bk-button
                text
                theme="primary"
                class="mr-8"
                onClick={() => handleShowCreateSubscribeRuleSlider(data)}>
                { t('数据订阅') }
              </bk-button>
            )}
            {
              data.isOnline ? (
                <OperationBtnStatusTips data={data}>
                  <auth-button
                    text
                    theme="primary"
                    disabled={Boolean(data.operationTicketId)}
                    class="mr-8"
                    action-id="mysql_enable_disable"
                    permission={data.permission.mysql_enable_disable}
                    resource={data.id}
                    onClick={() => handleSwitchCluster(TicketTypes.MYSQL_HA_DISABLE, data)}>
                    { t('禁用') }
                  </auth-button>
                </OperationBtnStatusTips>
              ) : (
                <>
                  <OperationBtnStatusTips data={data}>
                    <auth-button
                      text
                      theme="primary"
                      disabled={data.isStarting}
                      class="mr-8"
                      action-id="mysql_enable_disable"
                      permission={data.permission.mysql_enable_disable}
                      resource={data.id}
                      onClick={() => handleSwitchCluster(TicketTypes.MYSQL_HA_ENABLE, data)}>
                      { t('启用') }
                    </auth-button>
                  </OperationBtnStatusTips>
                  <OperationBtnStatusTips data={data}>
                    <auth-button
                      text
                      theme="primary"
                      disabled={Boolean(data.operationTicketId)}
                      class="mr-8"
                      action-id="mysql_destroy"
                      permission={data.permission.mysql_destroy}
                      resource={data.id}
                      onClick={() => handleDeleteCluster(data)}>
                      { t('删除') }
                    </auth-button>
                  </OperationBtnStatusTips>
                </>
              )
            }
          </>
        ),
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['master_domain'].includes(item.field as string),
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key && key !== 'id') as string[],
    showLineHeight: false,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBHA_TABLE_SETTINGS, defaultSettings);

  const getMenuList = async (item: SearchSelectItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, state.filters);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (state.filters || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  const fetchData = (loading?:boolean) => {
    const params = getSearchSelectorParams(state.filters);
    tableRef.value.fetchData(params, {}, loading);
    isInit.value = false;
  };

  const handleOpenEntryConfig = (row: TendbhaModel) => {
    showEditEntryConfig.value  = true;
    clusterId.value = row.id;
  };

  const handleSelection = (data: TendbhaModel, list: TendbhaModel[]) => {
    state.selected = list;
    selectedClusterList.value = list;
  };

  const handleShowAuthorize = (selected: TendbhaModel[] = []) => {
    authorizeState.isShow = true;
    authorizeState.selected = selected;
  };

  const handleShowCreateSubscribeRuleSlider = (data?: ColumnData['data']) => {
    if (data) {
      // 单个集群订阅
      selectedClusterList.value = [data];
    }
    showCreateSubscribeRuleSlider.value = true;
  };

  const handleClearSelected = () => {
    state.selected = [];
    authorizeState.selected = [];
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  /**
   * 获取模块列表
   */
  const fetchModules = () => getModules({
    bk_biz_id: globalBizsStore.currentBizId,
    cluster_type: ClusterTypes.TENDBHA,
  }).then((res) => {
    state.dbModuleList = res.map(item => ({
      id: item.db_module_id,
      name: item.name,
    }));
    return state.dbModuleList;
  });
  fetchModules();

  const handleClearSearch = () => {
    state.filters = [];
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleSearch = () => {
    fetchData();
  };

  /**
   * 集群启停
   */
  const handleSwitchCluster = (type: TicketTypesStrings, data: TendbhaModel) => {
    if (!type) return;

    const isOpen = type === TicketTypes.MYSQL_HA_ENABLE;
    const title = isOpen ? t('确定启用该集群') : t('确定禁用该集群');
    useInfoWithIcon({
      type: 'warnning',
      title,
      content: () => (
        <div style="word-break: all;">
          {
            isOpen
              ? <p>{t('集群【name】启用后将恢复访问', { name: data.cluster_name })}</p>
              : <p>{t('集群【name】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { name: data.cluster_name })}</p>
          }
        </div>
      ),
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: type,
            details: {
              cluster_ids: [data.id],
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  /**
   * 删除集群
   */
  const handleDeleteCluster = (data: TendbhaModel) => {
    const { cluster_name: name } = data;
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定删除该集群'),
      confirmTxt: t('删除'),
      confirmTheme: 'danger',
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{t('集群【name】被删除后_将进行以下操作', { name })}</p>
          <p>{t('1_删除xx集群', { name })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name })}</p>
          <p>3. {t('回收主机')}</p>
        </div>
      ),
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: TicketTypes.MYSQL_HA_DESTROY,
            details: {
              cluster_ids: [data.id],
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyHa',
      query: {
        bizId: globalBizsStore.currentBizId,
        from: route.name as string,
      },
    });
  };

  onMounted(() => {
    if (route.query.id && !clusterId.value) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.mysql-ha-cluster-list {
  height: 100%;
  padding: 24px 0;
  margin: 0 24px;
  overflow: hidden;

  .operation-box{
    display: flex;
    flex-wrap: wrap;

    .bk-search-select {
      flex: 1;
      max-width: 320px;
      min-width: 320px;
      margin-left: auto;
    }
  }

  .table-wrapper {
    background-color: white;

    .bk-table {
      height: 100% !important;
    }

    :deep(.bk-table-body) {
      max-height: calc(100% - 100px);
    }
  }

  .is-shrink-table {
    :deep(.bk-table-body) {
      overflow: hidden auto;
    }
  }

  :deep(.cell) {
    line-height: normal !important;

    .domain {
      display: flex;
      align-items: center;
    }

    .db-icon-copy, .db-icon-edit {
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
    .db-icon-copy, .db-icon-edit {
      display: inline-block !important;
    }
  }

  :deep(.is-offline) {
    a {
      color: @gray-color;
    }

    .cell {
      color: @disable-color;
    }
  }

  :deep(.cluster-name-container) {
    display: flex;
    align-items: center;
    padding: 8px 0;
    overflow: hidden;

    .cluster-name {
      line-height: 16px;

      &__alias {
        color: @light-gray;
      }
    }

    .cluster-tags {
      display: flex;
      margin-left: 4px;
      align-items: center;
      flex-wrap: wrap;
    }

    .cluster-tag {
      margin: 2px 0;
      flex-shrink: 0;
    }
  }
}
</style>
