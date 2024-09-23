<template>
  <div class="instance-list-page">
    <div class="header-action">
      <BkDropdown
        @hide="() => (isInstanceDropdown = false)"
        @show="() => (isInstanceDropdown = true)">
        <BkButton
          class="dropdown-button"
          :class="{ active: isInstanceDropdown }">
          {{ t('申请实例') }}
          <DbIcon type="up-big dropdown-button-icon" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleGoApply('MongoDBReplicaSetApply')">
              {{ t('副本集集群') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleGoApply('MongoDBSharedClusterApply')">
              {{ t('分片集群实例') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DropdownExportExcel
        export-type="instance"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="mongodb" />
      <DbSearchSelect
        class="header-select"
        :data="searchSelectData"
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
        :data-source="getMongoInstancesList"
        releate-url-query
        :row-class="setRowClass"
        selectable
        :settings="settings"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import  {
    getMongoInstancesList,
    getMongoRoleList,
  } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import {
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  import { getSearchSelectorParams } from '@utils';

  const instanceData = defineModel<{
    instanceAddress: string,
    clusterId: number,
  }>('instanceData');

  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const router = useRouter();
  const { t } = useI18n();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: [
      ClusterTypes.MONGO_SHARED_CLUSTER,
      ClusterTypes.MONGO_REPLICA_SET
    ].join(',') as ClusterTypes,
    attrs: ['role'],
    isCluster: false,
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const tableRef = ref();
  const isInstanceDropdown = ref(false);

  const roleListType = ref<{
    id: string,
    name: string
  }[]>([]);

  const selected = ref<MongodbInstanceModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.bk_host_id));

  const searchSelectData = computed(() => [
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'running',
          name: t('正常'),
        },
        {
          id: 'unavailable',
          name: t('异常'),
        },
      ],
    },
    {
      name: t('部署角色'),
      id: 'role',
      multiple: true,
      children: searchAttrs.value.role,
    },
    {
      name: t('端口'),
      id: 'port',
    },
    {
      name: t('集群架构'),
      id: 'cluster_type',
      multiple: true,
      children: [
        {
          id: ClusterTypes.MONGO_REPLICA_SET,
          name: t('副本集'),
        },
        {
          id: ClusterTypes.MONGO_SHARED_CLUSTER,
          name: t('分片集群'),
        },
      ],
    },
  ]);

  const columns = computed(() => {
    const list = [
      {
        label: t('实例'),
        field: 'instance_address',
        width: 200,
        minWidth: 180,
        fixed: 'left',
        showOverflowTooltip: false,
        render: ({ data }: { data: MongodbInstanceModel }) => (
          <div style="display: flex; align-items: center;">
            <div class="text-overflow" v-overflow-tips>
              <bk-button
                text
                theme="primary"
                onClick={ () => handleToDetails(data) }>
                  { data.instance_address }
              </bk-button>
            </div>
            {
              data.isRebooting && (
                <db-icon
                    svg
                    type="zhongqizhong"
                    class="cluster-tag ml-8"
                    style="width: 38px; height: 16px;" />
              )
            }
          </div>
      ),
      },
      {
        label: t('角色'),
        field: 'role',
        filter: {
          list: columnAttrs.value.role,
          checked: columnCheckedMap.value.role,
        },
      },
      {
        label: t('状态'),
        field: 'status',
        filter: {
          list: [
            {
              value: 'running',
              text: t('正常'),
            },
            {
              value: 'unavailable',
              text: t('异常'),
            },
          ],
          checked: columnCheckedMap.value.status,
        },
        render: ({ data }: { data: MongodbInstanceModel }) => {
          const { text, theme } = data.dbStatusConfigureObj;
          return <DbStatus type="linear" theme={ theme }>{ text }</DbStatus>;
        },
      },
      {
        label: t('所属集群'),
        field: 'cluster_name',
        fixed: 'left',
        showOverflowTooltip: false,
        render: ({ data }: { data: MongodbInstanceModel }) => (
          <div class="text-overflow" v-overflow-tips>
            <router-link
              to={{
                name: data.cluster_type === 'MongoReplicaSet' ? 'MongoDBReplicaSetList' : 'MongoDBSharedClusterList',
                query: { name: data.cluster_name },
                 }}>
                { data.cluster_name }
            </router-link>
          </div>
        ),
      },
      {
        label: t('集群架构'),
        field: 'cluster_type',
        filter: {
          list: [
            {
              value: ClusterTypes.MONGO_REPLICA_SET,
              text: t('副本集'),
            },
            {
              value: ClusterTypes.MONGO_SHARED_CLUSTER,
              text: t('分片集群'),
            },
          ],
          checked: columnCheckedMap.value.cluster_type,
        },
        render: ({ data }: { data: MongodbInstanceModel }) => data.clusterTypeText,
      },
      {
        label: t('分片名'),
        field: 'shard',
        render: ({ data }: { data: MongodbInstanceModel }) => data.shard || '--',

      },
      {
        label: t('部署时间'),
        field: 'createAtDisplay',
        sort: true,
      },
      {
        label: t('操作'),
        field: 'operation',
        fixed: 'right',
        minWidth: 210,
        render: ({ data } : { data: MongodbInstanceModel }) => (
          <>
            <OperationBtnStatusTips data={data}>
              <bk-button
                text
                class="mr8"
                disabled={data.isRebooting}
                theme='primary'
                onClick={ () => handleChangeInstanceOnline(data, true) }>
                  { t('重启') }
              </bk-button>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips data={data}>
              <bk-button
                text
                style={{ display: 'none' }}
                theme='primary'
                disabled={data.operationDisabled}
                onClick={ () => handleChangeInstanceOnline(data, false) }>
                  { t('禁用') }
              </bk-button>
            </OperationBtnStatusTips>
          </>
        ),
      },
    ];
    if (isStretchLayoutOpen.value) {
      list.pop();
    }
    return list;
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key && key !== 'id') as string[],
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.MONGODB_INSTANCE_TABLE_SETTINGS, defaultSettings);

  useRequest(getMongoRoleList, {
    onSuccess(data) {
      roleListType.value = data.map(item => ({
        id: item,
        name: item,
      }));
    },
  });

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value.fetchData(
      {
        ...getSearchSelectorParams(searchValue.value),
      },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ...sortValue
      },
      loading
    )
    isInit = false;
  };

  const handleChangeInstanceOnline = (
    data: MongodbInstanceModel,
    flag: boolean,
  ) => {
    InfoBox({
      title: flag ? t('确认重启该实例？') : t('确认禁用该实例'),
      subTitle: t('实例：name', { name: data.ip }),
      confirmText: t('确认'),
      cancelText: t('取消'),
      infoType: 'warning',
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: async () => {
        const type = flag ? TicketTypes.MONGODB_INSTANCE_RELOAD : TicketTypes.MONGODB_DISABLE;
        const params = {
          bk_biz_id: currentBizId,
          ticket_type: type,
          details: {
            infos: [
              {
                cluster_id: data.cluster_id,
                bk_host_id: data.bk_host_id,
                port: data.port,
                role: data.role,
              },
            ],
          },
        };
        await createTicket(params)
          .then((res) => {
            ticketMessage(res.id);
          });
      },
    });
  };

  const handleGoApply = (name: string) => {
    router.push({
      name,
    });
  };

  const handleSelection = (
    data: MongodbInstanceModel,
    list: MongodbInstanceModel[],
  ) => {
    selected.value = list;
  };

  // 设置行样式
  const setRowClass = (data: MongodbInstanceModel) => {
    const classStack = [];
    if (data.isNew) {
      classStack.push('is-new-row');
    }
    if (
      instanceData.value
      && data.cluster_id === instanceData.value.clusterId
      && data.instance_address === instanceData.value.instanceAddress
    ) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: MongodbInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
    };
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      padding-bottom: 16px;
      flex-wrap: wrap;

      .header-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }
</style>
