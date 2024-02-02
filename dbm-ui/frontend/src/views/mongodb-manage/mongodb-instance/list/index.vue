<template>
  <div class="instance-list-page">
    <div class="header-action">
      <BkDropdown
        @hide="() => isInstanceDropdown = false"
        @show="() => isInstanceDropdown = true">
        <BkButton
          class="dropdown-button"
          :class="{ 'active': isInstanceDropdown }">
          {{ t('实例申请') }}
          <DbIcon type="up-big dropdown-button-icon" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleGoApply('mongoDBReplicaSetApply')">
              {{ t('副本集集群') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleGoApply('mongoDBSharedClusterApply')">
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
        v-model="searchValues"
        class="header-select"
        :data="searchData"
        :placeholder="t('请输入关键字或选择条件搜索')"
        @change="handleFetchTableData" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getMongoInstancesList"
        :is-anomalies="isAnomalies"
        :pagination="renderPagination"
        :pagination-extra="{ small: false }"
        :row-class="setRowClass"
        selectable
        :settings="settings"
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
    type IPagination,
    useDefaultPagination,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';

  import { getSearchSelectorParams } from '@utils';

  const instanceData = defineModel<{
    instanceAddress: string,
    clusterId: number,
  }>('instanceData');

  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const router = useRouter();
  const { t } = useI18n();

  const statusList = [
    {
      text: t('正常'),
      value: 'running',
    },
    {
      text: t('异常'),
      value: 'unavailable',
    },
  ];

  const clusterList = [
    {
      text: t('副本集'),
      value: 'MongoReplicaSet',
    },
    {
      text: t('分片集群'),
      value: 'MongoShardedCluster',
    },
  ];

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const tableRef = ref();
  const isAnomalies = ref(false);
  const isInstanceDropdown = ref(false);

  const roleListType = ref<{
    id: string,
    name: string
  }[]>([]);

  const searchValues = ref([]);
  const selected = ref<MongodbInstanceModel[]>([]);
  const pagination = ref<IPagination>(useDefaultPagination());

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.bk_host_id));

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
        fixed: 'left',
        showOverflowTooltip: false,
        filter: {
          list: roleListType.value.map(item => ({
            text: item.name,
            value: item.name,
          })),
        },
      },
      {
        label: t('状态'),
        field: 'status',
        showOverflowTooltip: false,
        render: ({ data }: { data: MongodbInstanceModel }) => {
          const { text, theme } = data.dbStatusConfigureObj;
          return <DbStatus type="linear" theme={ theme }>{ text }</DbStatus>;
        },
        filter: {
          list: statusList,
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
        render: ({ data }: { data: MongodbInstanceModel }) => data.clusterTypeText,
        filter: {
          list: clusterList,
        },
      },
      {
        label: t('分片名'),
        field: 'shard',
      },
      {
        label: t('地域'),
        field: 'slave_domain',
      },
      {
        label: t('部署时间'),
        field: 'create_at',
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

  const searchData = computed(() => [
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
    {
      name: t('从域名'),
      id: 'slave_domain',
    },
    {
      name: t('角色'),
      id: 'role',
      multiple: true,
      children: roleListType.value,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: statusList.map(item => ({
        id: item.value,
        name: item.text,
      })),
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key && key !== 'id') as string[],
    showLineHeight: false,
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

  const handleFetchTableData = () => {
    tableRef.value.fetchData({
      ...getSearchSelectorParams(searchValues.value),
    }, {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
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
        try {
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
          return true;
        } catch (_) {
          return false;
        }
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
  @import "@styles/mixins.less";

  .instance-list-page{
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      padding-bottom: 16px;
      flex-wrap: wrap;

      .header-select{
        flex: 1;
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }
</style>
