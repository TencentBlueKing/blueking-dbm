<template>
  <div class="instance-list-page">
    <div class="header-action">
      <BkButton
        class="mb16 "
        theme="primary"
        @click="handleGoApply">
        {{ t('实例申请') }}
      </BkButton>
      <DropdownExportExcel
        export-type="instance"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="mongodb" />
      <DbSearchSelect
        v-model="searchValues"
        :data="searchData"
        :placeholder="t('请输入关键字或选择条件搜索')"
        style=" flex: 1;max-width: 320px;
        min-width: 320px;margin-left: auto;"
        @change="fetchTableData" />
    </div>
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': isStretchLayoutOpen}">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getUserList"
        :is-anomalies="isAnomalies"
        :pagination="renderPagination"
        :pagination-extra="{small:false}"
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

  import   InstanceListModel from '@services/model/mongodb/instance-list';
  import type { PayloadType } from '@services/source/instanceview';
  import  { getRoleList, getUserList } from '@services/source/instanceview';

  import {  type IPagination, useDefaultPagination, useStretchLayout  } from '@hooks';

  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';

  import {
    getSearchSelectorParams,
  } from '@utils';

  import type { SearchSelectValues, TableColumnRender  } from '@/types/bkui-vue';

  interface ColumnData {
    cell: string,
    data: InstanceListModel
  }

  interface Emits {
    (e: 'getPayload', value:PayloadType): void
  }

  const emits = defineEmits<Emits>();
  const statusMap = {
    running: '正常',
    unavailable: '异常',
  } as Record<string, string>;
  const router = useRouter();
  const { t } = useI18n();

  const tableRef = ref();
  const isAnomalies = ref(false);
  const filterListType = ref<{id:string, name:string}[]>([]);
  const searchValues = ref<SearchSelectValues>([]);
  const selected = ref<InstanceListModel[]>([]);
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.bk_host_id));

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const pagination = ref<IPagination>(useDefaultPagination());

  const columns = computed(() => {
    const list = [
      {
        label: t('实例'),
        field: 'instance_address',
        fixed: 'left',
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
          <div style="display: flex; align-items: center;">
            <div class="text-overflow" v-overflow-tips>
              <bk-button text theme="primary"  onClick={() => handleToDetails(data)}>
                {cell}
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
          list: filterListType.value.map(item => ({
            text: item.name, value: item.name,
          })),
        },
      },
      {
        label: t('状态'),
        field: 'status',
        showOverflowTooltip: false,
        render: ({ data }:  {  data: InstanceListModel }) => {
          const { text, flag } = data.getStuts;
          return <DbStatus type="linear" theme={flag}>{text}</DbStatus>;
        },
        filter: {
          list: Object.keys(statusMap).map(id => ({
            text: t(statusMap[id]), value: id,
          })),
        },
      },
      {
        label: t('所属集群'),
        field: 'cluster_name',
        fixed: 'left',
        showOverflowTooltip: false,
        render: ({ data, cell }: TableColumnRender) => (
          <div class="text-overflow" v-overflow-tips>
            <router-link
              to={{
                name: InstanceListModel.staticClusterType === 'replicaset' ? 'replicaSetList' : 'sharedClusterList',
                params: { id: data.cluster_name },
                }}>
              { cell }
            </router-link>
          </div>
        ),
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
        render: ({ data } : { data: InstanceListModel }) => (
          <>
            <OperationStatusTips class="mr8">
              <bk-button text theme='primary' onClick={() => changesState(data, true)}>
                { t('重启') }
              </bk-button>
            </OperationStatusTips>
            <OperationStatusTips>
              <bk-button   text   theme='primary' onClick={() => changesState(data, false)}>
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
      children: filterListType.value,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: Object.keys(statusMap).map((id: string) => ({
        id,
        name: t(statusMap[id]),
      })),
    },
  ]);

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

  useRequest(getRoleList, {
    onSuccess(data) {
      filterListType.value = data.map(item => ({
        id: item,
        name: item,
      }));
    },
  });

  const fetchTableData = () => {
    tableRef.value.fetchData({
      ...getSearchSelectorParams(searchValues.value),
    }, {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };

  const changesState = (data:InstanceListModel, flag:boolean) => {
    InfoBox({
      title: (
        flag ? <span title={t('确认重启该实例？')}>
       { t('确认重启该实例？')}
        </span> : <span title={t('确认禁用该实例')}>
       { t('确认禁用该实例')}
        </span>
      ),
      subTitle: (
        <span title={t('实例：name', { name: data.ip })}>
       {t('实例：name', { name: data.ip })}
        </span>
      ),
      confirmText: t('确认'),
      cancelText: t('取消'),
      infoType: 'warning',
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
      },
    });
  };

  const handleGoApply = () => {
    router.push({
      name: 'instanceList',
    });
  };

  const instanceData = defineModel<{instanceAddress:string, clusterId:number}>('instanceData');

  const handleSelection = (data: InstanceListModel, list: InstanceListModel[]) => {
    selected.value = [...list];
  };

  // 设置行样式
  const setRowClass = (data: InstanceListModel) => {
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
  const handleToDetails = (data :InstanceListModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
    };
    emits('getPayload', data.getPayload);
  };

  onBeforeMount(() => {
    InstanceListModel.prototype.switchClusterType(false);
  });
</script>
<style lang="less" scoped>
  @import "@/styles/mixins.less";

  .instance-list-page{
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      padding-bottom: 16px;
      flex-wrap: wrap;
    }
  }
</style>
