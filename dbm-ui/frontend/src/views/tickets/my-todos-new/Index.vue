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
  <div class="my-todos">
    <div class="my-todos-top">
      <div class="my-todos-top__left">
        <PanelTab
          v-model="tabActive"
          :panels="panels"
          @change="handleClickTab" />
        <BkButton
          class="ml-8"
          theme="primary"
          @click="handleClickBatch">
          {{ buttonText }}
        </BkButton>
      </div>
      <DbSearchSelect
        class="search-bar"
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="dataSource"
      :pagination="pagination"
      primary-key="ticket_id"
      selectable
      :settings="tableSettings"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @selection="handleSelectionChange" />
    <ConfirmDialog
      :is-show="dialogObj.isShow"
      :tag-config="dialogObj.tagConfig"
      :title="dialogObj.title"
      @close="dialogObj.isShow = false"
      @submit="handleSubmit" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { findRelatedClusters } from '@services/clusters'
  import type { ListBase } from '@services/types';

  import ConfirmDialog, { type IFormData, type Props as ConfirmDialogProps, type TagItem, type TagLayout } from './components/ConfirmDialog.vue'
  // import { getTicketsList, getTicketTypeCount } from '@services/ticket';
  import PanelTab, { type PanelListItem } from './components/PanelTab.vue';
  import RowData from './RowData.json'

  import { useCopy, useLinkQueryColumnSerach } from '@/hooks';
  import { processTicketTodo } from '@/services/source/ticket';
  import { useGlobalBizs } from '@/stores';
  import { getSearchSelectorParams } from '@/utils';

  enum TabNames {
    APPROVAL = 'approval',
    CONFIRM = 'confirm',
    REPLENISH = 'replenishment',
  }
  enum DialogOperate {
    ADOPT = 'adopt',
    REFUSE = 'refuse',
    EXEC = 'execute',
    STOP = 'stop',
  }
  interface DataSourceSearchParams {
    resource_type: TabNames;// 组件类型
    ticket_id: number;
    bk_biz_name: string;
    ticket_type: string;
    cluster_name: string;
    status_display: string;
    creator: string;
    create_at: string
  }
  interface DataRow {
    id: number;
    ticket_id: string | number; // 单号
    ticket_type_display: string; // 单据类型展示
    ticket_type: string; // 单据类型
    bk_biz_id: number; // 业务id
    bk_biz_name: string; // 业务名
    cluster_id: number; // 集群id
    cluster_name: string; // 集群名
    audit_node: string; // 当前步骤
    remark: string; // 备注
    updater: string; // 当前处理人
    status: string; // 状态
    creator: string; // 提单人
    create_at: string; // 提单时间
    group?: string; // 数据库类型
    permission?: {
      ticket_view?: boolean;
    };
  }


  const { t } = useI18n();
  const copy = useCopy();
  const { currentBizId } = useGlobalBizs();
  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    columnCheckedMap,
    columnFilterChange,
    clearSearchValue,
    handleSearchValueChange,
    // searchType 要后端配置，暂用spotty_host
  } = useLinkQueryColumnSerach('spotty_host', [], () => fetchData());

  const dialogTagConfig: Record<DialogOperate, Omit<ConfirmDialogProps, 'isShow'>> = {
    [DialogOperate.ADOPT]: {
      title: t('单据审批'),
      tagConfig: {
        data: [
          { name: t('通过'), action: 'APPROVE', theme: 'success', desc: t('通过后，单据将继续往下流转') }
        ]
      },
    },
    [DialogOperate.REFUSE]: {
      title: t('单据审批'),
      tagConfig: {
        data: [
          { name: t('拒绝'), action: 'TERMINATE', theme: 'danger', desc: t('拒绝后，单据将被终止') }
        ]
      },
    },
    [DialogOperate.EXEC]: {
      title: t('单据执行确认'),
      tagConfig: {
        data: [
          { name: t('确认执行'), action: 'APPROVE', theme: 'success' }
        ]
      },
    },
    [DialogOperate.STOP]: {
      title: t('单据终止确认'),
      tagConfig: {
        data: [
          { name: t('终止单据'), action: 'TERMINATE', theme: 'danger' }
        ]
      }
    },
  }

  const tabActive = ref<PanelListItem['name']>(TabNames.APPROVAL);
  const panels = shallowRef<PanelListItem[]>([
    { name: TabNames.APPROVAL, label: t('待我审批'), count: 0 },
    { name: TabNames.CONFIRM, label: t('待我确认'), count: 0 },
    { name: TabNames.REPLENISH, label: t('待我补货'), count: 0 },
  ]);
  const tableRef = ref();
  const currentRow = ref<DataRow>();
  const selectedList = shallowRef<DataRow[]>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const isHovered = ref<Record<string, boolean>>({})
  const dialogObj = reactive<ConfirmDialogProps & { isBatch: boolean }>({
    isShow: false,
    title: '',
    tagConfig: {
      layout: 'horizontal' as TagLayout,
      data: [] as TagItem[]
    },
    isBatch: false // 是否批量
  })

  const buttonText = computed(()=> {
    const [panelInfo] = panels.value.filter(item=>item.name === tabActive.value)
    return t(`批量${panelInfo.label.slice(2)}`)
  })
  const searchSelectData = computed(() => [
    {
      name: t('单号'),
      id: 'ticket_id',
      multiple: true,
    },
    {
      name: t('业务'),
      id: 'bk_biz_id',
      multiple: true,
      children: searchAttrs.value.bk_biz_ids
    },
    {
      name: t('单据类型'),
      id: 'ticket_type',
      multiple: true,
      children: searchAttrs.value.ticket_types,
    },
    {
      name: t('集群'),
      id: 'cluster_name',
      multiple: true,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'adopt',
          name: t('通过'),
        },
        {
          id: 'refuse',
          name: t('拒绝'),
        },
        {
          id: 'ing',
          name: t('审批中'),
        },
      ],
    },
    {
      name: t('提单人'),
      id: 'creator',
      multiple: true,
    },
    {
      name: t('提单时间'),
      id: 'create_at',
      multiple: true,
    },
  ]);
  const tableSettings = computed(() => ({
    fields: columns.value.slice(1).filter((item) => item.field).map((item) => ({
      label: item.label as string,
      field: item.field as string,
    })),
    checked: columns.value.slice(1).map((item) => item.field).filter((key) => !!key) as string[],
  }));
  const columns = computed(()=>[
    {
      label: t('单号'),
      field: 'ticket_id',
      fixed: 'left',
      width: 80,
      render: ({ data }: { data: DataRow }) =>
            <auth-router-link
              to={{
                name: 'bizTicketManage',
                query: {
                  id: data.ticket_id,
                },
              }}
              action-id="ticket_view"
              resource={data.ticket_id}
              permission={data.permission?.ticket_view}
              target="_blank">
                {data.ticket_id || '--'}
            </auth-router-link>,
    },
    {
      label: t('业务'),
      field: 'bk_biz_id',
      width: 80,
      filter: {
        list: columnAttrs.value.bk_biz_ids,
        checked: columnCheckedMap.value.bk_biz_id,
      },
      render: ({ data }: { data: DataRow }) => data.bk_biz_name || '--',
    },
    {
      label: t('单据类型'),
      field: 'ticket_type',
      width: 180,
      filter: {
        list: columnAttrs.value.ticket_types,
        checked: columnCheckedMap.value.ticket_types,
      },
      render: ({ data }: { data: DataRow }) => data.ticket_type_display || '--',
    },
    {
      label: t('集群'),
      field: 'cluster_id',
      width: 300,
      render: ({ data }: { data: DataRow }) =>
        <>
        <div
          onMouseenter={()=>isHovered.value[data.ticket_id] = true}
          onMouseleave={()=>isHovered.value[data.ticket_id] = false}>
          {data.cluster_name || '--'}
          {
            isHovered.value[data.ticket_id] ?
            <db-icon
              class="ml-8 cluster-copy-icon"
              v-bk-tooltips={t('复制该单据关联的所有集群')}
              type="copy"
              onClick={()=>copyRelatedCluster(data)} />
            :<></>
          }
        </div>
        </>
    },
    {
      label: t('当前步骤'),
      field: 'audit_node',
      width: 100,
      render: ({ data }: { data: DataRow }) => data.audit_node || '--',
    },
    {
      label: t('当前处理人'),
      field: 'updater',
      width: 150,
      render: ({ data }: { data: DataRow }) => data.updater || '--',
    },
    {
      label: t('状态'),
      field: 'status',
      width: 120,
      filter: {
        list: [
          {
            value: 'adopting',
            text: t('审批中'),
          },
          {
            value: 'confirming',
            text: t('确认中'),
          },
        ],
        checked: columnCheckedMap.value.status,
      },
      render: ({ data }: { data: DataRow }) => {
        const statusThemeMap: Record<string, { text: string; theme?: string; customStyle?: string }> = {
          adopting: {
            text: t('审批中'),
            theme: 'warning'
          },
          confirming: {
            text: t('确认中'),
            customStyle: 'color: #5135ea; background: #f4eeff;'
          },
        }
        const mapper = statusThemeMap[data.status];
        return <bk-tag style={mapper.customStyle} theme={mapper.theme}>{mapper.text}</bk-tag>
      },
    },
    {
      label: t('备注'),
      field: 'remark',
      width: 180,
      render: ({ data }: { data: DataRow }) => data.remark || '--'
    },
    {
      label: t('提单人'),
      field: 'creator',
      width: 150,
      render: ({ data }: { data: DataRow }) => data.creator || '--',
    },
    {
      label: t('提单时间'),
      field: 'create_at',
      width: 180,
      render: ({ data }: { data: DataRow }) => data.create_at || '--',
    },
    {
      label: t('操作'),
      field: '',
      width: 220,
      fixed: 'right',
      render: ({ data }: { data: DataRow }) => (
            <>
            {data.status === 'adopting' ?
            <>
              <bk-button
                class="mr-8"
                theme="primary"
                text
                onClick={handleOperate.bind(null, data, DialogOperate.ADOPT)}>
                {t('通过')}
              </bk-button>
              <bk-button
                class="mr-8"
                theme="primary"
                text
                onClick={handleOperate.bind(null, data, DialogOperate.REFUSE)}>
                {t('拒绝')}
              </bk-button>
              </> : <>
              <bk-button
                class="mr-8"
                theme="primary"
                text
                onClick={handleOperate.bind(null, data, DialogOperate.EXEC)}>
                {t('确认执行')}
              </bk-button>
              <bk-button
                class="mr-8"
                theme="primary"
                text
                onClick={handleOperate.bind(null, data, DialogOperate.STOP)}>
                {t('终止单据')}
              </bk-button>
              </> }
              <bk-button
                theme="primary"
                text
                onClick={handleOperate.bind(null, data)}>
                {t('再次提单')}
              </bk-button>
            </>
          ),
    },
  ]);

  const handleOperate = (data: DataRow, action: DialogOperate) => {
    currentRow.value = data;
    const obj = dialogTagConfig[action]
    dialogObj.isShow = true;
    dialogObj.title = obj.title;
    dialogObj.tagConfig = obj.tagConfig;
  }
  const handleSubmit = async ({ action, content }: IFormData) => {
    if(dialogObj.isBatch) {
      // batchTodo
      const ticketIds = [...selectedList.value].map(item => item.ticket_id)
      console.log(ticketIds, 'ticketIds');
      return
    }
    processTicketTodo({
      action,
      todo_id: currentRow.value?.id as number,
      ticket_id: currentRow.value?.ticket_id as number,
      params: {
        content
      },
    }).then(()=>{
      fetchData()
    })
  }
  const handleClickTab = async (value: PanelListItem['name']) => {
    tabActive.value = value;
    fetchData()
  };
  const getTabCount = async () => {
    // const res = await getTicketTypeCount()
    // local mock、、代接口开发后删掉即可
    const res: Record<TabNames, number> = {
      approval: 100,
      confirm: 20,
      replenishment: 0,
    };
    const newPanels: PanelListItem[] = ([...panels.value] as PanelListItem[]).reduce((result, item) => {
      const count = res[item.name as TabNames];
      result.push({ ...item, count });
      return result;
    }, [] as PanelListItem[]);
    panels.value = newPanels;
  };
  // 获取数据
  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef!.value.fetchData({
      ...searchParams,
      resource_type: tabActive.value
    });
  };
  // local mock 、、代接口开发后删掉即可
  const dataSource = async (params: DataSourceSearchParams): Promise<ListBase<DataRow[]>> => {
    console.log(params, 'search params');

    const { resource_type: type } = params
    if(type === TabNames.APPROVAL) {
      return {
        count: RowData.result.length,
        next: '',
        previous: '',
        results: RowData.result,
        permission: {},
      }
    } if (type === TabNames.CONFIRM) {
      return {
        count: RowData.result.length - 1,
        next: '',
        previous: '',
        results: RowData.result.slice(1),
        permission: {},
      }
    }if (type === TabNames.REPLENISH) {
      return {
        count: RowData.result.length - 2,
        next: '',
        previous: '',
        results: RowData.result.slice(2),
        permission: {},
      }
    }
    return {
      count: 0,
      next: '',
      previous: '',
      results: [],
      permission: {},
    }
  }
  const handleClickBatch = async () => {
    // const res = await api()
    if (tabActive.value === TabNames.APPROVAL) {
      dialogObj.isShow = true;
      dialogObj.title = t('批量审批');
      dialogObj.tagConfig = {
        layout: 'vertical',
        data: [
          { name: t('通过'), action: 'APPROVE', theme: 'success', desc: t('通过后，单据将继续往下流转') },
          { name: t('拒绝'), action: 'TERMINATE', theme: 'danger', desc: t('拒绝后，单据将被终止') }
        ]
      };
      dialogObj.isBatch = true;
    }else if (tabActive.value === TabNames.CONFIRM) {
      dialogObj.isShow = true;
      dialogObj.title = t('批量确认');
      dialogObj.tagConfig = {
        data: [
          { name: t('确认执行'), action: 'APPROVE', theme: 'success' },
          { name: t('终止单据'), action: 'TERMINATE', theme: 'danger' }
        ]
      };
      dialogObj.isBatch = true;
    }
  };
  const handleSelectionChange = (idList: number[], list: DataRow[]) => {
    selectedList.value = list;
  };
  const copyRelatedCluster = async ({ group, cluster_id: clusterId, cluster_name }: DataRow) => {
    // 只有这三种有关联集群
    const configDbs = ['mysql', 'mongodb', 'sqlserver'];
    if (!configDbs.includes(group as string)) {
      copy(cluster_name)
      return
    }
    const [firstItem] = await findRelatedClusters({
      dbType: group as 'mysql' | 'mongodb' | 'sqlserver',
      bizId: currentBizId,
      cluster_ids: [clusterId]
    })
    const line = firstItem.related_clusters.map(item=>item.cluster_name).join(';')
    copy(line)
  }

  onMounted(()=>{
    getTabCount();
    fetchData();
  })
</script>

<style lang="less">
  .my-todos {
    height: 100%;
    padding: 16px 24px;
    background-color: @white-color;

    .my-todos-top {
      display: flex;
      justify-content: space-between;
      margin-bottom: 16px;

      .my-todos-top__left {
        display: flex;
        flex: 1;
      }

      .search-bar {
        flex: 1;
      }
    }

    .cluster-copy-icon {
      position: relative;
      top: -1px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
