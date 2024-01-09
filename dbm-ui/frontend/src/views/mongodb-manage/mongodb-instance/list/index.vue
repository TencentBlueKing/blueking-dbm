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
        :data-source="getInstanceList"
        :is-anomalies="isAnomalies"
        :pagination="renderPagination"
        :pagination-extra="{ small: false }"
        :row-class="setRowClass"
        selectable
        @selection="handleSelection" />
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
    getInstanceList,
    getRoleList,
  } from '@services/source/mongodbInstance';
  import { createTicket } from '@services/source/ticket';

  import {
    type IPagination,
    useDefaultPagination,
    useStretchLayout,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import type { SearchSelectValues } from '@/types/bkui-vue';

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

  const searchValues = ref<SearchSelectValues>([]);
  const selected = ref<MongodbInstanceModel[]>([]);
  const pagination = ref<IPagination>(useDefaultPagination());

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.bk_host_id));

  const columns = computed(() => {
    const list = [
      {
        label: t('实例'),
        field: 'instance_address',
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
          const { text, theme } = data.dbStatusconfigureObj;
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
                name: data.cluster_type === 'MongoReplicaSet'
                ? 'mongoDBReplicaSetList'
                : 'mongoDBSharedClusterList',
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
            <OperationStatusTips class="mr8">
              <bk-button
                text
                theme='primary'
                onClick={ () => handleChangeInstanceOnline(data, true) }>
                  { t('重启') }
              </bk-button>
            </OperationStatusTips>
            <OperationStatusTips>
              <bk-button
                text
                theme='primary'
                onClick={ () => handleChangeInstanceOnline(data, false) }>
                  { t('禁用') }
              </bk-button>
            </OperationStatusTips>
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

  useRequest(getRoleList, {
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
      title: (flag
        ? <span title={ t('确认重启该实例？') }>{ t('确认重启该实例？') }</span>
        : <span title={ t('确认禁用该实例') }>{ t('确认禁用该实例') }</span>
      ),
      subTitle: <span>{ t('实例：name', { name: data.ip }) }</span>,
      confirmText: t('确认'),
      cancelText: t('取消'),
      infoType: 'warning',
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: async () => {
        try {
          const type = flag ? TicketTypes.MONGODB_ENABLE : TicketTypes.MONGODB_DISABLE;
          const params = {
            bk_biz_id: currentBizId,
            ticket_type: type,
            details: {
              cluster_ids: [data.cluster_id],
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
      data.cluster_id === instanceData.value?.clusterId
      && data.instance_address === instanceData.value?.instanceAddress
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
