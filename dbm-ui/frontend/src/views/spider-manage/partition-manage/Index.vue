<template>
  <div class="spider-manage-paritition-page">
    <div class="header-action mb-16">
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleCreate">
        {{ t('新建') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleBatchRemove"
        :content="t('移除后将不可恢复')"
        :title="t('确认移除选中的策略')">
        <BkButton
          class="ml-8"
          :disabled="selectionList.length < 1">
          {{ t('删除') }}
        </BkButton>
      </DbPopconfirm>
      <DbSearchSelect
        v-model="searchValues"
        :data="serachData"
        :placeholder="t('输入关键字或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        unique-select
        @change="handleSearch" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="getList"
      :row-class="getRowClass"
      selectable
      :settings="tableSetting"
      @clear-search="handleClearSearch"
      @selection="handleTableSelection"
      @setting-change="handleSettingChange" />
    <DryRun
      v-model="isShowDryRun"
      :operation-dry-run-data="operationDryRunData"
      :partition-data="operationData" />
    <DbSideslider
      v-model:is-show="isShowOperation"
      :confirm-text="operationData && operationData.id ? t('保存并执行') : t('提交')"
      :title="operationData ? operationData.id ? t('编辑分区策略') :t('克隆分区策略') : t('新建分区策略')"
      :width="1000">
      <PartitionOperation
        :data="operationData"
        @success="handleOperationSuccess" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowExecuteLog"
      :title="t(`查看执行记录`)"
      :width="1000">
      <ExecuteLog
        v-if="operationData"
        :data="operationData" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import {
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PartitionModel from '@services/model/partition/partition';
  import {
    batchRemove,
    disablePartition,
    dryRun,
    enablePartition,
    getList,
  } from '@services/partitionManage';

  import { ClusterTypes } from '@common/const';

  import {
    getSearchSelectorParams,
    isRecentDays,
    messageSuccess,
  } from '@utils';

  import DryRun from './components/DryRun.vue';
  import ExecuteLog from './components/ExecuteLog.vue';
  import PartitionOperation from './components/Operation.vue';
  import useTableSetting from './hooks/useTableSetting';

  const { t } = useI18n();

  const {
    setting: tableSetting,
    handleChange: handleSettingChange,
  } = useTableSetting();

  const tableRef = ref();
  const searchValues = ref([]);
  const isShowOperation = ref(false);
  const isShowExecuteLog = ref(false);
  const isShowDryRun = ref(false);
  const executeLoadingMap = ref<Record<number, boolean>>({});
  const selectionList = shallowRef<number[]>([]);
  const operationData = shallowRef<PartitionModel>();
  const operationDryRunData = shallowRef<ServiceReturnType<typeof dryRun>>();

  const serachData = [
    {
      name: t('域名'),
      id: 'immute_domains',
    },
    {
      name: t('DB 名'),
      id: 'dblikes',
    },
    {
      name: t('表名'),
      id: 'tblikes',
    },
  ];

  const tableColumn = [
    {
      label: t('策略 ID'),
      field: 'id',
      fixed: true,
      render: ({ data }: {data: PartitionModel}) => (
        <span>
          <span>{data.id}</span>
          {
          isRecentDays(data.create_time, 24 * 3)
            ? <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />
            : null
        }
        </span>
      ),
    },
    {
      label: t('集群域名'),
      field: 'immute_domain',
      width: 240,
    },
    {
      label: t('DB 名'),
      field: 'dblike',
      width: 150,
      render: ({ data }: {data: PartitionModel}) => {
        if (!data.dblike) {
          return '--';
        }
        return <bk-tag>{data.dblike}</bk-tag>;
      },
    },
    {
      label: t('表名'),
      field: 'tblike',
      width: 150,
      render: ({ data }: {data: PartitionModel}) => {
        if (!data.tblike) {
          return '--';
        }
        return <bk-tag>{data.tblike}</bk-tag>;
      },
    },
    {
      label: t('分区字段'),
      field: 'partition_columns',
    },
    {
      label: t('分区字段类型'),
      field: 'partition_column_type',
    },
    {
      label: t('分区间隔（天）'),
      field: 'partition_time_interval',
    },
    {
      label: t('数据过期时间（天）'),
      field: 'expire_time',
      minWidth: 150,
    },
    {
      label: t('最近一次执行状态'),
      field: 'status',
      minWidth: 150,
      render: ({ data }: {data: PartitionModel}) => (
        <div>
          <db-icon
            class={{ 'rotate-loading': data.isRunning }}
            style="vertical-align: middle;"
            type={data.statusIcon}
            svg />
          <span class="ml-4">{data.statusText}</span>
        </div>
      ),
    },
    {
      label: t('最近一次执行时间'),
      field: 'execute_time',
      minWidth: 180,
    },
    {
      label: t('操作'),
      field: 'action',
      width: 200,
      fixed: 'right',
      render: ({ data }: { data: PartitionModel }) => {
        const renderAction = () => {
          if (data.isRunning) {
            return (
              <router-link
                to={{
                  name: 'SelfServiceMyTickets',
                  query: {
                    filterId: data.ticket_id,
                  },
                }}
                target="_blank">
                {t('查看')}
              </router-link>
            );
          }
          if (!data.isEnabled) {
            return (
              <bk-button
                theme="primary"
                text
                onClick={() => handleEnable(data)}>
                {t('启用')}
              </bk-button>
            );
          }
          return (
            <bk-button
              theme="primary"
              text
              loading={executeLoadingMap.value[data.id]}
              onClick={() => handleExecute(data)}>
              {t('执行')}
            </bk-button>
          );
        };
        return (
        <>
          {renderAction()}
          <span
            v-bk-tooltips={{
              content: t('正在执行中，无法编辑'),
              disabled: !data.isRunning,
            }}
            class="ml-8">
            <bk-button
              theme="primary"
              text
              disabled={data.isRunning}
              onClick={() => handleEdit(data)}>
              {t('编辑')}
            </bk-button>
          </span>
          <bk-button
            class="ml-8"
            theme="primary"
            text
            onClick={() => handleShowExecuteLog(data)}>
            {t('执行记录')}
          </bk-button>
          <more-action-extend class="ml-8">
            {{
              default: () => (
                <>
                  {
                    data.isEnabled && (
                      <div onClick={() => handleDisable(data)}>
                        { t('禁用') }
                      </div>
                    )
                  }
                  <div onClick={() => handleClone(data)}>
                    { t('克隆') }
                  </div>
                  <db-popconfirm
                    confirm-handler={() => handleRemove(data)}
                    content={t('删除操作无法撤回，请谨慎操作！')}
                    title={t('确认删除该分区策略？')}>
                    <span>{ t('删除') }</span>
                  </db-popconfirm>
                </>
              ),
            }}
          </more-action-extend>
        </>
        );
      },
    },
  ];

  const getRowClass = (data: PartitionModel) => (isRecentDays(data.create_time, 24 * 3) ? 'is-new-row' : '');

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    tableRef.value?.fetchData(searchParams, {
      cluster_type: ClusterTypes.TENDBCLUSTER,
    });
  };

  // 新建
  const handleCreate = () => {
    operationData.value = undefined;
    isShowOperation.value = true;
  };


  // 批量删除
  const handleBatchRemove = () => {
    operationData.value = undefined;
    return batchRemove({
      cluster_type: ClusterTypes.TENDBCLUSTER,
      ids: selectionList.value,
    }).then(() => {
      fetchData();
      Object.values(selectionList.value).forEach((hostId) => {
        tableRef.value.removeSelectByKey(hostId);
      });
      selectionList.value = [];
      messageSuccess(t('移除成功'));
    });
  };

  // 搜索
  const handleSearch = () => {
    fetchData();
  };

  const handleTableSelection = (payload: number[]) => {
    selectionList.value = payload;
  };

  // 清空搜索
  const handleClearSearch = () => {
    searchValues.value = [];
    fetchData();
  };

  // 执行
  const handleExecute = (payload: PartitionModel) => {
    isShowDryRun.value = true;
    operationData.value = payload;
    operationDryRunData.value = undefined;
    console.log('operationData = ', operationData.value);
  };
  // 编辑
  const handleEdit  = (payload: PartitionModel) => {
    isShowOperation.value = true;
    operationData.value = payload;
  };
  // 执行记录
  const handleShowExecuteLog = (payload: PartitionModel) => {
    isShowExecuteLog.value = true;
    operationData.value = payload;
    operationDryRunData.value = undefined;
  };

  // 新建、编辑成功
  const handleOperationSuccess = (payload: ServiceReturnType<typeof dryRun>) => {
    fetchData();
    operationDryRunData.value = payload;
    operationData.value = undefined;
    isShowDryRun.value = true;
  };

  const handleDisable  =  (payload: PartitionModel) => {
    disablePartition({
      cluster_type: ClusterTypes.TENDBCLUSTER,
      ids: [payload.id],
    }).then(() => {
      fetchData();
      messageSuccess(t('禁用成功'));
    });
  };

  const handleEnable = (payload: PartitionModel) => {
    enablePartition({
      cluster_type: ClusterTypes.TENDBCLUSTER,
      ids: [payload.id],
    }).then(() => {
      fetchData();
      messageSuccess(t('启用成功'));
    });
  };

  const handleClone = (payload: PartitionModel) => {
    operationData.value = payload;
    operationData.value.id = 0;
    isShowOperation.value = true;
  };

  const handleRemove = (payload: PartitionModel) => batchRemove({
    cluster_type: ClusterTypes.TENDBCLUSTER,
    ids: [payload.id],
  }).then(() => {
    fetchData();
    messageSuccess(t('移除成功'));
  });
</script>
<style lang="less">
  .spider-manage-paritition-page {
    .header-action{
      display: flex;
    }

    .more-action{
      display: flex;
      width: 32px;
      height: 32px;
      font-size: 14px;
      cursor: pointer;
      border-radius: 50%;
      align-items: center;
      justify-content: center;

      &:hover{
        background: #dcdee5;
      }
    }
  }
</style>
