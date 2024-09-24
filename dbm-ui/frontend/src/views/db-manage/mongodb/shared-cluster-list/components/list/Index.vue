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
  <div class="shared-cluster-list">
    <div class="header-action">
      <BkButton
        class="mb-8"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </BkButton>
      <BkButton
        class="ml-8 mb-8"
        :disabled="!hasSelected"
        @click="handleShowClusterAuthorize">
        {{ t('批量授权') }}
      </BkButton>
      <span
        v-bk-tooltips="{
          disabled: hasData,
          content: t('请先申请集群'),
        }"
        class="inline-block">
        <BkButton
          class="ml-8 mb-8"
          :disabled="!hasData"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
      </span>
      <DropdownExportExcel
        class="ml-8 mb-8"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="mongodb" />
      <ClusterIpCopy :selected="selected" />
      <DbSearchSelect
        class="header-action-search-select"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      class="shared-cluster-list-table"
      :columns="columns"
      :data-source="getMongoList"
      releate-url-query
      :row-class="setRowClass"
      selectable
      :settings="tableSetting"
      show-overflow-tips
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings" />
  </div>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.MONGODB"
    :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
    :selected="selected"
    @success="handleClearSelected" />
  <ExcelAuthorize
    v-model:is-show="excelAuthorizeShow"
    :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
    :ticket-type="TicketTypes.MONGODB_EXCEL_AUTHORIZE" />
  <DbSideslider
    v-if="detailData"
    v-model:is-show="capacityChangeShow"
    :disabled-confirm="!isCapacityChange"
    :width="960">
    <template #header>
      <span>
        {{ t('MongoDB 集群容量变更【xxx】', [detailData.clusterName]) }}
        <BkTag theme="info">
          {{ t('存储层') }}
        </BkTag>
      </span>
    </template>
    <CapacityChange
      v-model:is-change="isCapacityChange"
      :data="detailData" />
  </DbSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import {
    getMongoInstancesList,
    getMongoList,
  } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';
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
    AccountTypes,
    ClusterTypes,
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import DbTable from '@components/db-table/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/ClusterAuthorize.vue';
  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue'
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderInstances from '@views/db-manage/common/render-instances/RenderInstances.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTag.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams ,
  } from '@utils';

  import { useDisableCluster } from '../../hooks/useDisableCluster';
  import CapacityChange from '../components/CapacityChange.vue';

  const clusterId = defineModel<number>('clusterId');

  const { t } = useI18n();
  const copy = useCopy();
  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const disableCluster = useDisableCluster();
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
    searchType: ClusterTypes.MONGO_SHARED_CLUSTER,
    attrs: [
      'bk_cloud_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const searchSelectData = computed(() => [
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
      multiple: true,
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
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
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const capacityChangeShow = ref(false);
  const isCapacityChange = ref(false);
  const detailData = ref<{
    id: number,
    clusterName: string,
    specId: number,
    specName: string
    bizId: number,
    cloudId: number,
    shardNum: number,
    shardNodeCount: number,
  }>();
  const clusterAuthorizeShow = ref(false);
  const excelAuthorizeShow = ref(false);
  const selected = ref<MongodbModel[]>([])

  const tableDataList = computed(() => tableRef.value?.getData<MongodbModel>() || [])
  const hasData = computed(() => tableDataList.value.length > 0);
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 60,
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 200,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: { data: MongodbModel }) => {
        const content = (
          <>
            {
              data.isNew && (
              <MiniTag
                content='NEW'
                theme='success' />
              )
            }
            {
              data.operationTagTips.map(item => (
                <RenderOperationTag
                  class="ml-4"
                  data={item} />
              ))
            }
            {
              data.isDisabled && (
                <db-icon
                  svg
                  type="yijinyong"
                  class="disabled-tag" />
              )
            }
          </>
        );

        return (
          <div>
            <RenderTextEllipsisOneLine
              text={data.cluster_name}
              textStyle={{
                fontWeight: '700',
              }}
              onClick={() => handleToDetails(data.id)}>
              {content}
            </RenderTextEllipsisOneLine>
            <span class="cluster-alias">{ data.cluster_alias }</span>
          </div>
        );
      },
    },
    {
      label: t('主域名'),
      field: 'master_domain',
      width: 280,
      minWidth: 280,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'master_domain',
                label: t('域名')
              },
            ]
          }
        >
          {t('主域名')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: MongodbModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <span>{data.masterDomainDisplayName || '--'}</span>
            ),
            append: () => (
              <>
                <RenderCellCopy copyItems={
                  [
                    {
                      value: data.master_domain,
                      label: t('域名')
                    },
                    {
                      value: data.masterDomainDisplayName,
                      label: t('域名:端口')
                    }
                  ]
                } />
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: { data: MongodbModel }) => <span>{data.bk_cloud_name || '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      width: 100,
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
      render: ({ data }: { data: MongodbModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: { data: MongodbModel }) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('MongoDB版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
      render: ({ data }: { data: MongodbModel }) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ data }: { data: MongodbModel }) => <span>{data.bk_cloud_name || '--'}</span>,
    },
    {
      label: 'ConfigSvr',
      field: 'mongo_config',
      width: 180,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'mongo_config')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'mongo_config')}
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
          {'ConfigSvr'}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: MongodbModel }) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.mongo_config}
          title={`【${data.master_domain}】ConfigSvr`}
          role="mongo_config"
          clusterId={data.id}
          dataSource={getMongoInstancesList}/>
      ),
    },
    {
      label: 'Mongos',
      field: 'mongos',
      width: 180,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'mongos')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'mongos')}
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
          {'Mongos'}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: MongodbModel }) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.mongos}
          title={`【${data.master_domain}】Mongos`}
          role="mongos"
          clusterId={data.id}
          dataSource={getMongoInstancesList}/>
      ),
    },
    {
      label: 'ShardSvr',
      field: 'mongodb',
      width: 180,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'mongodb')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'mongodb')}
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
          {'ShardSvr'}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: MongodbModel }) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.mongodb}
          title={`【${data.master_domain}】ShardSvr`}
          role="mongodb"
          clusterId={data.id}
          dataSource={getMongoInstancesList}/>
      ),
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 140,
      render: ({ data }: { data: MongodbModel }) => <span>{data.updater || '--'}</span>,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 160,
      render: ({ data }: { data: MongodbModel }) => <span>{data.updateAtDisplay || '--'}</span>,
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ data }: { data: MongodbModel }) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      sort: true,
      width: 160,
      render: ({ data }: { data: MongodbModel }) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
      render: ({ data }: { data: MongodbModel }) => <span>{data.cluster_time_zone || '--'}</span>,
    },
    {
      label: t('操作'),
      width: 300,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: { data: MongodbModel }) => {
        const baseButtons = [
          <bk-button
            text
            theme="primary"
            onclick={() => handleCopyMasterDomainDisplayName(data)}>
            { t('复制访问地址') }
          </bk-button>,
        ];
        const onlineButtons = [
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={data.operationDisabled}
              onclick={() => handleCapacityChange(data)}>
              { t('集群容量变更') }
            </bk-button>
          </OperationBtnStatusTips>,
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={data.operationDisabled}
              onclick={() => handleDisableCluster(data)}>
              { t('禁用') }
            </bk-button>
          </OperationBtnStatusTips>,
        ];
        const offlineButtons = [
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={data.isStarting}
              onclick={() => handleEnableCluster(data)}>
              { t('启用') }
            </bk-button>
          </OperationBtnStatusTips>,
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={Boolean(data.operationTicketId)}
              onclick={() => handleDeleteCluster(data)}>
              { t('删除') }
            </bk-button>
          </OperationBtnStatusTips>,
        ];

        if (data.isOnline) {
          return [...baseButtons, ...onlineButtons];
        }
        return [...baseButtons, ...offlineButtons];
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['cluster_name'].includes(item.field as string),
    })),
    checked: [
      'cluster_name',
      'master_domain',
      'status',
      'cluster_stats',
      'major_version',
      'region',
      'mongo_config',
      'mongos',
      'mongodb',
    ],
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.MONGODB_SHARED_CLUSTER_SETTINGS, defaultSettings);

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
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

  const setRowClass = (row: MongodbModel) => {
    const classList = [];
    if (row.isNew) {
      classList.push('is-new');
    }
    if (!row.isOnline) {
      classList.push('is-offline');
    }
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.join(' ');
  };

  const handleApply = () => {
    router.push({
      name: 'MongoDBSharedClusterApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleSelection = (key: number[], list: Record<any, any>[]) => {
    selected.value = list as MongodbModel[];
  };

  const handleShowClusterAuthorize = () => {
    clusterAuthorizeShow.value = true;
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleClearSelected = () => {
    selected.value = [];
  };

  const handleCopyMasterDomainDisplayName = (row: MongodbModel) => {
    copy(row.masterDomainDisplayName);
  };

  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleCapacityChange = (row: MongodbModel) => {
    const {
      id,
      cluster_name: clusterName,
      bk_biz_id: bizId,
      bk_cloud_id: cloudId,
      shard_num: shardNum,
      shard_node_count: shardNodeCount,
      mongodb,
    } = row;
    const {
      id: specId,
      name,
    } = mongodb[0].spec_config;

    detailData.value = {
      id,
      clusterName,
      specId,
      specName: name,
      bizId,
      cloudId,
      shardNum,
      shardNodeCount
    };
    capacityChangeShow.value = true;
  };

  const handleEnableCluster = (row: MongodbModel) => {
    InfoBox({
      type: 'warning',
      title: t('确定启用该集群'),
      content: () => (
        <p>
          { t('集群') }：
          <span class='info-box-cluster-name'>
            { row.cluster_name }
          </span>
        </p>
      ),
      confirmText: t('启用'),
      onConfirm: async () => {
        await createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.MONGODB_ENABLE,
          details: {
            cluster_ids: [row.id],
          },
        })
          .then((res) => {
            ticketMessage(res.id);
          });
      },
    });
  };

  const handleDisableCluster = (row: MongodbModel) => {
    disableCluster(row);
  };

  const handleDeleteCluster = (row: MongodbModel) => {
    const { cluster_name: name } = row;
    InfoBox({
      type: 'warning',
      title: t('确定删除该集群'),
      confirmText: t('删除'),
      confirmButtonTheme: 'danger',
      contentAlign: 'left',
      content: () => (
        <div class="cluster-delete-content">
          <p>{t('集群【name】被删除后_将进行以下操作', { name })}</p>
          <p>{t('1_删除xx集群', { name })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name })}</p>
          <p>3. {t('回收主机')}</p>
        </div>
      ),
      onConfirm: async () => {
        await createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.MONGODB_DESTROY,
          details: {
            cluster_ids: [row.id],
          },
        })
          .then((res) => {
            ticketMessage(res.id);
          });
      },
    });
  };

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValue.value),
      cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
    }, {...sortValue}, loading);
    isInit = false;
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
  const getInstanceListByRole = (dataList: MongodbModel[], field: keyof MongodbModel) => dataList.reduce((result, curRow) => {
    result.push(...curRow[field] as MongodbModel['mongodb']);
    return result;
  }, [] as MongodbModel['mongodb']);

  const handleCopySelected = <T,>(field: keyof T, role?: keyof MongodbModel) => {
    if(role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field)
      return;
    }
    handleCopy(selected.value as T[], field)
  }

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof MongodbModel) => {
    const allData = await tableRef.value!.getAllData<MongodbModel>();
    if(allData.length === 0) {
      Message({
        theme: 'primary',
        message: '暂无数据可复制',
      });
      return;
    }
    if(role) {
      handleCopy(getInstanceListByRole(allData, role) as T[], field)
      return;
    }
    handleCopy(allData as T[], field)
  }
</script>

<style>
  .info-box-cluster-name {
    color: #313238;
  }

  .cluster-delete-content {
    padding-left: 16px;
    text-align: left;
    word-break: all;
  }
</style>

<style lang="less" scoped>
  .shared-cluster-list {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 8px;

      .header-action-search-select {
        width: 500px;
        margin-left: auto;
      }

      .header-action-deploy-time {
        width: 300px;
        margin-left: 8px;
      }
    }

    :deep(.shared-cluster-list-table) {
      .is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }

      .is-offline {
        .cell {
          color: #c4c6cc !important;
        }
      }

      .new-tag {
        height: 19px;
      }

      .disabled-tag {
        width: 38px;
        height: 16px;
        margin-left: 4px;
      }

      .cluster-alias {
        color: #979ba5 !important;
      }

      td div.cell .db-icon-copy {
        display: none;
        margin-top: 2px;
        margin-left: 4px;
        color: #3a84ff;
        color: @primary-color;
        cursor: pointer;
      }

      th:hover,
      td:hover {
        .db-icon-copy {
          display: inline-block !important;
          margin-left: 4px;
          color: #3a84ff;
          vertical-align: middle;
          cursor: pointer;
        }
      }
    }
  }
</style>
