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
  <div class="riak-list-container">
    <div class="header-action">
      <AuthButton
        action-id="riak_cluster_apply"
        theme="primary"
        @click="toApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        :ids="selectedIds"
        type="riak" />
      <ClusterIpCopy :selected="selected" />
      <DbSearchSelect
        :data="serachData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        @change="handleSearchValueChange" />
      <BkDatePicker
        v-model="deployTime"
        append-to-body
        clearable
        :placeholder="t('请选择xx', [t('部署时间')])"
        type="daterange"
        @change="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      class="riak-list-table"
      :columns="columns"
      :data-source="getRiakList"
      :row-class="setRowClass"
      selectable
      :settings="tableSetting"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings" />
    <DbSideslider
      v-if="detailData"
      v-model:is-show="addNodeShow"
      quick-close
      :title="t('添加节点【xx】', [detailData.cluster_name])"
      :width="960">
      <AddNodes
        :data="detailData"
        @submit-success="fetchData" />
    </DbSideslider>
    <DbSideslider
      v-if="detailData"
      v-model:is-show="deleteNodeShow"
      :title="t('删除节点【xx】', [detailData.cluster_name])"
      :width="960">
      <DeleteNodes
        :data="detailData"
        @submit-success="fetchData" />
    </DbSideslider>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RiakModel from '@services/model/riak/riak';
  import {
    getRiakInstanceList,
    getRiakList,
  } from '@services/source/riak';
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

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import DbTable from '@components/db-table/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue'
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderNodeInstance from '@views/db-manage/common/RenderNodeInstance.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTag.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams,
  } from '@utils';

  import AddNodes from '../components/AddNodes.vue';
  import DeleteNodes from '../components/DeleteNodes.vue';

  interface Emits {
    (e: 'detailOpenChange', data: boolean): void
  }

  interface Expose {
    freshData: () => void
  }

  const emits = defineEmits<Emits>();
  const clusterId = defineModel<number>('clusterId');

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const copy = useCopy();
  const { currentBizId } = useGlobalBizs();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const ticketMessage = useTicketMessage();
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
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.RIAK,
    attrs: [
      'bk_cloud_id',
      'db_module_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const serachData = computed(() => [
    {
      name: t('集群名称'),
      id: 'name',
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
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('模块'),
      id: 'db_module_id',
      multiple: true,
      children: searchAttrs.value.db_module_id,
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
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ] as ISearchItem[]);

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const deployTime = ref<[string, string]>(['', '']);
  const addNodeShow = ref(false);
  const deleteNodeShow = ref(false);
  const detailData = ref<RiakModel>();
  const selected = ref<RiakModel[]>([])

  const selectedIds = computed(() => selected.value.map(item => item.id));
  const hasSelected = computed(() => selected.value.length > 0);

  const columns = computed(() => [
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 240,
      fixed: 'left',
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
      render: ({ data }: { data: RiakModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="riak_view"
                permission={data.permission.riak_view}
                resource={data.id}
                text
                theme="primary"
                onClick={() => handleToDetail(data.id)}>
                { data.cluster_name }
              </auth-button>
            ),
            append: () => (
              <>
                {
                  data.isNewRow && (
                  <MiniTag
                      content='NEW'
                      theme='success'
                      class='new-tag'>
                    </MiniTag>
                  )
                }
                {
                  data.operationTagTips.map(item => <RenderOperationTag class="ml-4" data={item}/>)
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
            )
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('版本'),
      field: 'major_version',
      width: 80,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
      render: ({ data }: { data: RiakModel }) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_id',
      width: 140,
      showOverflowTooltip: true,
      filter: {
        list: columnAttrs.value.db_module_id,
        checked: columnCheckedMap.value.db_module_id,
      },
      render: ({ data }: { data: RiakModel }) => <span>{data.db_module_name || '--'}</span>,
    },
    {
      label: t('管控区域'),
      width: 120,
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: { data: RiakModel }) => <span>{data.bk_cloud_name || '--'}</span>,
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
      render: ({ data }: { data: RiakModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: { data: RiakModel }) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('节点'),
      field: 'riak_node',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'riak_node')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'riak_node')}
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
          {t('节点')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: RiakModel }) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="riak_node"
          title={`【${data.cluster_name}】${t('节点')}`}
          clusterId={data.id}
          originalList={data.riak_node.map(nodeItem => ({
            ip: nodeItem.ip,
            port: nodeItem.port,
            status: nodeItem.status,
          }))}
          dataSource={ getRiakInstanceList } />
      ),
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 100,
      render: ({ data }: { data: RiakModel }) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 160,
      sort: true,
      render: ({ data }: { data: RiakModel }) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('操作'),
      width: 300,
      fixed: 'right',
      render: ({ data }: { data: RiakModel }) => (
        data.isOnline
          ? <>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id="riak_cluster_scale_in"
                  permission={data.permission.riak_cluster_scale_in}
                  resource={data.id}
                  text
                  theme="primary"
                  disabled={data.isOffline}
                  onClick={() => handleAddNodes(data)}
                >
                  { t('添加节点') }
                </auth-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id="riak_cluster_scale_out"
                  permission={data.permission.riak_cluster_scale_out}
                  resource={data.id}
                  text
                  class="ml-16"
                  theme="primary"
                  disabled={data.isOffline}
                  onClick={() => handleDeleteNodes(data)}
                >
                  { t('删除节点') }
                </auth-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id="riak_enable_disable"
                  permissionn={data.permission.riak_enable_disable}
                  resource={data.id}
                  text
                  class="ml-16"
                  theme="primary"
                  disabled={data.operationDisabled}
                  onClick={() => handlDisabled(data)}
                >
                  { t('禁用') }
                </auth-button>
              </OperationBtnStatusTips>
            </>
          : <>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id="riak_enable_disable"
                  permissionn={data.permission.riak_enable_disable}
                  resource={data.id}
                  text
                  theme="primary"
                  disabled={data.isStarting}
                  onClick={() => handleEnabled(data)}
                >
                  { t('启用') }
                </auth-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id="riak_cluster_destroy"
                  permission={data.permission.riak_cluster_destroy}
                  resource={data.id}
                  text
                  class="ml-16"
                  theme="primary"
                  disabled={Boolean(data.operationTicketId)}
                  onClick={() => handleDelete(data)}
                >
                  { t('删除') }
                </auth-button>
              </OperationBtnStatusTips>
            </>
      ),
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['cluster_name'].includes(item.field as string),
    })),
    checked: [
      'cluster_name',
      'major_version',
      'region',
      'db_module_id',
      'status',
      'cluster_stats',
      'riak_node',
    ],
    trigger: 'manual' as const,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.RIAK_TABLE_SETTINGS, defaultSettings);

  watch(isStretchLayoutOpen, (newVal) => {
    emits('detailOpenChange', newVal);
  });

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

  const setRowClass = (row: RiakModel) => {
    const classList = [];

    if (row.isNewRow) {
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

  const toApply = () => {
    router.push({
      name: 'RiakApply',
      query: {
        bizId: currentBizId,
      },
    });
  };

  const handleSelection = (key: number[], list: Record<any, any>[]) => {
    selected.value = list as RiakModel[];
  };

  const handleToDetail = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleAddNodes = (data: RiakModel) => {
    detailData.value = data;
    addNodeShow.value = true;
  };

  const handleDeleteNodes = (data: RiakModel) => {
    detailData.value = data;
    deleteNodeShow.value = true;
  };

  const handlDisabled = (data: RiakModel) => {
    InfoBox({
      title: t('确定禁用该集群', { name: data.cluster_name }),
      subTitle: (
        <>
          <p>{ t('集群') }：<span class='info-box-cluster-name'>{ data.cluster_name }</span></p>
          <p>{ t('被禁用后将无法访问，如需恢复访问，可以再次「启用」') }</p>
        </>
      ),
      infoType: 'warning',
      confirmText: t('禁用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_DISABLE,
          details: {
            cluster_id: data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };

  const handleEnabled = (data: RiakModel) => {
    InfoBox({
      title: t('确定启用该集群'),
      subTitle: (
        <>
          <p>{ t('集群') }：<span class='info-box-cluster-name'>{ data.cluster_name }</span></p>
          <p>{ t('启用后将恢复访问') }</p>
        </>
      ),
      infoType: 'warning',
      confirmText: t('启用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_ENABLE,
          details: {
            cluster_id: data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };

  const handleDelete = (data: RiakModel) => {
    InfoBox({
      title: t('确定删除该集群'),
      subTitle: (
        <>
          <p>{ t('集群') } ：<span class='info-box-cluster-name'>{ data.cluster_name }</span> , { t('被删除后将进行以下操作') }</p>
          <p>1. { t('删除xx集群', [data.cluster_name]) }</p>
          <p>2. { t('删除xx实例数据，停止相关进程', [data.cluster_name]) }</p>
          <p>3. { t('回收主机') }</p>
        </>
      ),
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('删除'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_DESTROY,
          details: {
            cluster_id: data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };

  const fetchData = (otherParamas: {
    status?: string
  } = {}) => {
    const params = {
      ...otherParamas,
      ...getSearchSelectorParams(searchValue.value),
    };
    const [startTime, endTime] = deployTime.value;
    if (startTime && endTime) {
      Object.assign(params, {
        start_time: dayjs(startTime).format('YYYY-MM-DD'),
        end_time: dayjs(endTime).format('YYYY-MM-DD '),
      });
    }

    tableRef.value!.fetchData({ ...params }, sortValue);
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
  const getInstanceListByRole = (dataList: RiakModel[], field: keyof RiakModel) => dataList.reduce((result, curRow) => {
    result.push(...curRow[field] as RiakModel['riak_node']);
    return result;
  }, [] as RiakModel['riak_node']);

  const handleCopySelected = <T,>(field: keyof T, role?: keyof RiakModel) => {
    if(role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field)
      return;
    }
    handleCopy(selected.value as T[], field)
  }

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof RiakModel) => {
    const allData = await tableRef.value!.getAllData<RiakModel>();
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


  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetail(Number(route.query.id));
    }
  });

  defineExpose<Expose>({
    freshData() {
      fetchData();
    },
  });
</script>

<style>
  .info-box-cluster-name {
    color: #313238;
  }
</style>

<style lang="less" scoped>
  .riak-list-container {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }

      .bk-date-picker {
        width: 300px;
        margin-left: 8px;
      }
    }

    :deep(.riak-list-table) {
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

      td .cell .db-icon-copy {
        display: none;
      }

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
