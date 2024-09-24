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
  <div class="hdfs-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'hdfs.clusterManage.instanceApply'"
        action-id="hdfs_apply"
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        v-db-console="'hdfs.clusterManage.export'"
        :ids="selectedIds"
        type="hdfs" />
      <ClusterIpCopy
        v-db-console="'hdfs.clusterManage.batchCopy'"
        :selected="selected" />
      <DbSearchSelect
        class="mb16"
        :data="serachData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="dataSource"
        :pagination-extra="paginationExtra"
        releate-url-query
        :row-class="getRowClass"
        selectable
        :settings="tableSetting"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      background-color="#F5F7FA"
      class="hdfs-manage-sideslider"
      quick-close
      :title="t('xx扩容【name】', { title: 'HDFS', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      background-color="#F5F7FA"
      class="hdfs-manage-sideslider"
      quick-close
      :title="t('xx缩容【name】', { title: 'HDFS', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      render-directive="if"
      :title="t('获取访问方式')"
      :width="500">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
    <BkSideslider
      v-model:is-show="isShowSettings"
      class="settings-sideslider"
      quick-close
      render-directive="if"
      :title="t('查看访问配置')"
      :width="960">
      <ClusterSettings
        v-if="operationData"
        :cluster-id="operationData.id" />
    </BkSideslider>
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import HdfsModel from '@services/model/hdfs/hdfs';
  import {
    getHdfsDetail,
    getHdfsInstanceList,
    getHdfsList,
  } from '@services/source/hdfs';
  import { createTicket  } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import {
    useCopy,
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    DBTypes,
    UserPersonalSettings,
  } from '@common/const';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue'
  import EditEntryConfig from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderNodeInstance from '@views/db-manage/common/RenderNodeInstance.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTag.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterExpansion from '@views/db-manage/hdfs/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/hdfs/common/shrink/Index.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  import ClusterSettings from './components/ClusterSettings.vue';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const { t, locale } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const ticketMessage = useTicketMessage();

  const copy = useCopy();
  const { currentBizId } = useGlobalBizs();
  const router = useRouter();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.HDFS,
    attrs: [
      'bk_cloud_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchTableData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const dataSource = getHdfsList;

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});

  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isShowSettings = ref(false);
  const isInit = ref(true);
  const operationData = shallowRef<HdfsModel>();
  const selected = ref<HdfsModel[]>([])
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isCN = computed(() => locale.value === 'zh-cn');
  const hasSelected = computed(() => selected.value.length > 0);
  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  const serachData = computed(() => [
    {
      name: t('访问入口'),
      id: 'domain',
      multiple: true,
    },
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
      multiple: true,
    },
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
        },
      ],
    },
    {
      name: t('版本'),
      id: 'major_version',
      multiple: true,
      children: searchAttrs.value.major_version,
    },
    {
      name: t('地域'),
      id: 'region',
      multiple: true,
      children: searchAttrs.value.region,
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);

  const getRowClass = (data: HdfsModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = isRecentDays(data.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 350 : 520;
    }
    return 100;
  });

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('访问入口'),
      field: 'domain',
      width: 280,
      minWidth: 280,
      fixed: 'left',
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'domain',
                label: t('域名')
              },
              {
                field: 'domainDisplayName',
                label: t('域名:端口')
              }
            ]
          }
        >
          {t('访问入口')}
        </RenderHeadCopy>
      ),
      render: ({ data }: {data: HdfsModel}) => (
          <TextOverflowLayout>
            {{
              default: () => (
                <auth-button
                  action-id="hdfs_view"
                  resource={data.id}
                  permission={data.permission.hdfs_view}
                  text
                  theme="primary"
                  onClick={() => handleToDetails(data.id)}>
                  {data.domainDisplayName}
                </auth-button>
              ),
              append: () => (
                <>
                  {data.domain && (
                    <RenderCellCopy copyItems={
                      [
                        {
                          value: data.domain,
                          label: t('域名')
                        },
                        {
                          value: data.domainDisplayName,
                          label: t('域名:端口')
                        }
                      ]
                    } />
                  )}
                  <span v-db-console="hdfs.clusterManage.modifyEntryConfiguration">
                    <EditEntryConfig
                      id={data.id}
                      getDetailInfo={getHdfsDetail}
                      permission={data.permission.access_entry_edit}
                      resource={DBTypes.HDFS}
                      onSuccess={fetchTableData} />
                  </span>
                </>
              ),
            }}
          </TextOverflowLayout>
        ),
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      width: 200,
      minWidth: 200,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'cluster_name'
              },
            ]
          }
        >
          {t('集群名称')}
        </RenderHeadCopy>
      ),
      render: ({ data }: {data: HdfsModel}) => (
        <div style="line-height: 14px; display: flex;">
          <div>
            <span>
              {data.cluster_name}
            </span>
            <div style='color: #C4C6CC;'>
              {data.cluster_alias || '--'}
            </div>
          </div>
          {
            data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
          }
          <db-icon
            v-show={!data.isOnline}
            svg
            type="yijinyong"
            style="width: 38px; height: 16px; margin-left: 4px;" />
          {
            isRecentDays(data.create_at, 24 * 3)
            && <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />
          }
            <db-icon
              class="mt-2"
              v-bk-tooltips={t('复制集群名称')}
              type="copy"
              onClick={() => copy(data.cluster_name)} />
        </div>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: {data: HdfsModel}) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      filter: {
        list: [
          {
            value: 'normal',
            text: t('正常'),
          },
          {
            value: 'abnormal',
            text: t('异常'),
          },
        ],
        checked: columnCheckedMap.value.status,
      },
      render: ({ data }: {data: HdfsModel}) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: {data: HdfsModel}) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ data }: {data: HdfsModel}) => <span>{data?.region || '--'}</span>,
    },
    {
      label: 'NameNode',
      field: 'hdfs_namenode',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'hdfs_namenode')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'hdfs_namenode')}
          config={
            [
              {
                label: 'IP',
                field: 'ip'
              },
              {
                label: t('实例'),
                field: 'instance'
              }
            ]
          }
        >
          {'NameNode'}
        </RenderHeadCopy>
      ),
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="hdfs_namenode"
          title={`【${data.domain}】NameNode`}
          clusterId={data.id}
          originalList={data.hdfs_namenode}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: 'Zookeeper',
      field: 'hdfs_zookeeper',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'hdfs_zookeeper')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'hdfs_zookeeper')}
          config={
            [
              {
                label: 'IP',
                field: 'ip'
              },
              {
                label: t('实例'),
                field: 'instance'
              }
            ]
          }
        >
          {'Zookeeper'}
        </RenderHeadCopy>
      ),
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="hdfs_zookeeper"
          title={`【${data.domain}】Zookeeper`}
          clusterId={data.id}
          originalList={data.hdfs_zookeeper}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: 'Journalnode',
      field: 'hdfs_journalnode',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'hdfs_journalnode')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'hdfs_journalnode')}
          config={
            [
              {
                label: 'IP',
                field: 'ip'
              },
              {
                label: t('实例'),
                field: 'instance'
              }
            ]
          }
        >
          {'Journalnode'}
        </RenderHeadCopy>
      ),
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="hdfs_journalnode"
          title={`【${data.domain}】Journalnode`}
          clusterId={data.id}
          originalList={data.hdfs_journalnode}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: 'DataNode',
      field: 'hdfs_datanode',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'hdfs_datanode')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'hdfs_datanode')}
          config={
            [
              {
                label: 'IP',
                field: 'ip'
              },
              {
                label: t('实例'),
                field: 'instance'
              }
            ]
          }
        >
          {'DataNode'}
        </RenderHeadCopy>
      ),
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="hdfs_datanode"
          title={`【${data.domain}】DataNode`}
          clusterId={data.id}
          originalList={data.hdfs_datanode}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: t('创建人'),
      field: 'creator',
    },
    {
      label: t('部署时间'),
      width: 160,
      field: 'create_at',
      sort: true,
      render: ({ data }: {data: HdfsModel}) => <span>{data.createAtDisplay}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: {data: HdfsModel}) => {
        const renderAction = (theme = 'primary') => {
          const baseAction = [
          <auth-button
            text
            theme="primary"
            action-id="hdfs_access_entry_view"
            permission={data.permission.hdfs_access_entry_view}
            v-db-console="hdfs.clusterManage.getAccess"
            resource={data.id}
            class="mr8"
            onClick={() => handleShowPassword(data)}>
            { t('获取访问方式') }
          </auth-button>,
          <auth-button
            text
            theme="primary"
            action-id="hdfs_view"
            permission={data.permission.hdfs_view}
            v-db-console="hdfs.clusterManage.viewAccessConfiguration"
            resource={data.id}
            class="mr8"
            onClick={() => handleShowSettings(data)}>
            { t('查看访问配置') }
          </auth-button>,
          ];
          if (data.isOffline) {
            return [
              <auth-button
                text
                theme="primary"
                action-id="hdfs_enable_disable"
                disabled={data.isStarting}
                permission={data.permission.hdfs_enable_disable}
                v-db-console="hdfs.clusterManage.enable"
                resource={data.id}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleEnable(data)}>
                { t('启用') }
              </auth-button>,
              <auth-button
                text
                theme="primary"
                action-id="hdfs_destroy"
                permission={data.permission.hdfs_destroy}
                v-db-console="hdfs.clusterManage.delete"
                resource={data.id}
                disabled={Boolean(data.operationTicketId)}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleRemove(data)}>
                { t('删除') }
              </auth-button>,
              ...baseAction,
            ];
          }
          return [
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="hdfs_scale_up"
                permission={data.permission.hdfs_scale_up}
                v-db-console="hdfs.clusterManage.scaleUp"
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowExpansion(data)}>
                { t('扩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="hdfs_shrink"
                permission={data.permission.hdfs_shrink}
                v-db-console="hdfs.clusterManage.scaleDown"
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowShrink(data)}>
                { t('缩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="hdfs_enable_disable"
                permission={data.permission.hdfs_enable_disable}
                v-db-console="hdfs.clusterManage.disable"
                resource={data.id}
                disabled={data.operationDisabled}
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handlDisabled(data)}>
                { t('禁用') }
              </auth-button>
            </OperationBtnStatusTips>,
            <a
              v-db-console="hdfs.clusterManage.manage"
              class="mr8"
              style={[theme === '' ? 'color: #63656e' : '']}
              href={data.access_url}
              target="_blank">
              { t('管理') }
            </a>,
            ...baseAction,
          ];
        };

        return (
          <>
            {renderAction()}
          </>
        );
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['domain'].includes(item.field as string),
    })),
    checked: [
      'domain',
      'status',
      'cluster_stats',
      'major_version',
      'region',
      'hdfs_namenode',
      'hdfs_zookeeper',
      'hdfs_journalnode',
      'hdfs_datanode',
    ],
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.HDFS_TABLE_SETTINGS, defaultSettings);

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, serachData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return serachData.value.filter(item => !selected.includes(item.id));
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
    return serachData.value.find(set => set.id === item.id)?.children || [];
  };

  const fetchTableData = (loading?:boolean) => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams, { ...sortValue }, loading);
    isInit.value = false;
  };

  const handleCopy = <T,>(dataList: T[], field: keyof T) => {
    const copyList = dataList.reduce((prevList, tableItem) => {
      const value = String(tableItem[field]);
      if (value && value !== '--' && !prevList.includes(value)) {
        prevList.push(value);
      }
      return prevList;
    }, [] as string[]);
    copy(copyList.join('\n'));
  }

  // 获取列表数据下的实例子列表
  const getInstanceListByRole = (dataList: HdfsModel[], field: keyof HdfsModel) => dataList.reduce((result, curRow) => {
    result.push(...curRow[field] as HdfsModel['hdfs_namenode']);
    return result;
  }, [] as HdfsModel['hdfs_namenode']);

  const handleCopySelected = <T,>(field: keyof T, role?: keyof HdfsModel) => {
    if(role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field)
      return;
    }
    handleCopy(selected.value as T[], field)
  }

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof HdfsModel) => {
    const allData = await tableRef.value!.getAllData<HdfsModel>();
    if(allData.length === 0) {
      Message({
        theme: 'primary',
        message: t('暂无数据可复制'),
      });
      return;
    }
    if(role) {
      handleCopy(getInstanceListByRole(allData, role) as T[], field)
      return;
    }
    handleCopy(allData as T[], field)
  }

  const handleSelection = (data: HdfsModel, list: HdfsModel[]) => {
    selected.value = list;
  };

  // 集群提单
  const handleGoApply = () => {
    router.push({
      name: 'HdfsApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 扩容
  const handleShowExpansion = (clusterData: HdfsModel) => {
    isShowExpandsion.value = true;
    operationData.value = clusterData;
  };

  // 缩容
  const handleShowShrink = (clusterData: HdfsModel) => {
    isShowShrink.value = true;
    operationData.value = clusterData;
  };

  // 禁用
  const handlDisabled =  (clusterData: HdfsModel) => {
    InfoBox({
      title: t('确认禁用【name】集群', { name: clusterData.cluster_name }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'HDFS_DISABLE',
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleEnable =  (clusterData: HdfsModel) => {
    InfoBox({
      title: t('确认启用【name】集群', { name: clusterData.cluster_name }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'HDFS_ENABLE',
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleRemove =  (clusterData: HdfsModel) => {
    InfoBox({
      title: t('确认删除【name】集群', { name: clusterData.cluster_name }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'HDFS_DESTROY',
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };

            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleShowPassword = (clusterData: HdfsModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  const handleShowSettings = (clusterData: HdfsModel) => {
    operationData.value = clusterData;
    isShowSettings.value = true;
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less" scoped>
  .hdfs-list-page {
    :deep(.cell) {
      line-height: normal !important;

      .domain {
        display: flex;
        align-items: center;
      }

      .db-icon-visible1 {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(tr:hover) {
      .db-icon-visible1 {
        display: inline-block !important;
      }
    }
  }
</style>
<style lang="less">
  .hdfs-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;

      .db-table,
      .audit-render-list,
      .bk-nested-loading {
        height: 100%;
      }

      .bk-table {
        height: 100% !important;
      }

      .bk-table-body {
        max-height: calc(100% - 100px);
      }
    }

    .is-shrink-table {
      .bk-table-body {
        overflow: hidden auto;
      }
    }

    .is-offline {
      * {
        color: #c4c6cc !important;
      }

      a,
      i,
      .bk-button.bk-button-primary .bk-button-text {
        color: #3a84ff !important;
      }
    }

    td div.cell .db-icon-copy {
      display: none;
      margin-left: 4px;
      color: #3a84ff;
      vertical-align: middle;
      cursor: pointer;
    }

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

    td:hover .db-icon-copy,
    th:hover .db-icon-copy {
      display: inline-block !important;
    }
  }

  .hdfs-manage-sideslider {
    .bk-modal-content {
      max-height: calc(100vh - 120px);
      overflow-y: auto;
    }
  }
</style>
