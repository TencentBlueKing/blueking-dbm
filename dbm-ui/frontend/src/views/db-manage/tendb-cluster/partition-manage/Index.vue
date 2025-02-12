<template>
  <div class="spider-manage-paritition-page">
    <div class="header-action mb-16">
      <AuthButton
        action-id="tendbcluster_partition_create"
        class="w-88"
        theme="primary"
        @click="handleCreate">
        {{ t('新建') }}
      </AuthButton>
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
      class="partition-table"
      :columns="tableColumn"
      :data-source="getList"
      :row-class="getRowClass"
      selectable
      :settings="tableSetting"
      show-settings
      @clear-search="handleClearSearch"
      @selection="handleTableSelection"
      @setting-change="handleSettingChange" />
    <DryRun
      v-model="isShowDryRun"
      :cluster-id="operationData?.cluster_id || operationDryRunDataClusterId"
      :operation-dry-run-data="operationDryRunData"
      :partition-data="operationData" />
    <PartitionOperation
      v-model:is-show="isShowOperation"
      :data="operationData"
      @create-success="handleOperationCreateSuccess"
      @edit-success="handleOperationEditSuccess" />
    <DbSideslider
      v-model:is-show="isShowExecuteLog"
      :show-footer="false"
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
  } from '@services/source/partitionManage';

  import { ClusterTypes } from '@common/const';

  import {
    getSearchSelectorParams,
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
  const operationDryRunDataClusterId = ref(0);
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
      fixed: 'left',
      width: 100,
      render: ({ data }: {data: PartitionModel}) => (
        <div class="id-container">
          <span>{data.id}</span>
          {
            data.isNew && (
              <bk-tag
                theme="success"
                size="small"
                class="ml-4">
                NEW
              </bk-tag>
            )
          }
          {
            data.isOffline && (
              <bk-tag
                class="ml-4"
                size="small">
                {t('已禁用')}
              </bk-tag>
            )
          }
        </div>
      ),
    },
    {
      label: t('集群域名'),
      field: 'immute_domain',
      width: 240,
      render: ({ data }: {data: PartitionModel}) => data.immute_domain || '--',
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
      width: 100,
      minWidth: 100,
      render: ({ data }: {data: PartitionModel}) => data.partition_columns || '--',
    },
    {
      label: t('分区字段类型'),
      field: 'partition_column_type',
      width: 150,
      minWidth: 150,
      render: ({ data }: {data: PartitionModel}) => data.partition_column_type || '--',
    },
    {
      label: t('分区间隔（天）'),
      field: 'partition_time_interval',
      width: 150,
      minWidth: 150,
      render: ({ data }: {data: PartitionModel}) => data.partition_time_interval || '--',
    },
    {
      label: t('数据过期时间（天）'),
      field: 'expire_time',
      width: 150,
      minWidth: 150,
      render: ({ data }: {data: PartitionModel}) => data.expire_time || '--',
    },
    {
      label: t('最近一次执行状态'),
      field: 'status',
      width: 150,
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
      width: 250,
      render: ({ data }: {data: PartitionModel}) => data.executeTimeDisplay || '--',
    },
    {
      label: t('操作'),
      width: 180,
      fixed: 'right',
      render: ({ data }: { data: PartitionModel }) => {
        const renderAction = () => {
          if (data.isRunning) {
            return (
              <router-link
                to={{
                  name: 'bizTicketManage',
                  params: {
                    ticketId: data.ticket_id,
                  },
                }}
                target="_blank">
                {t('查看')}
              </router-link>
            );
          }
          if (!data.isOnline) {
            return (
              <auth-button
                theme="primary"
                text
                action-id="tendb_partition_enable_disable"
                permission={data.permission.tendb_partition_enable_disable}
                resource={data.cluster_id}
                onClick={() => handleEnable(data)}>
                {t('启用')}
              </auth-button>
            );
          }
          return (
            <auth-button
              theme="primary"
              text
              action-id="tendbcluster_partition"
              permission={data.permission.tendbcluster_partition}
              resource={data.cluster_id}
              loading={executeLoadingMap.value[data.id]}
              onClick={() => handleExecute(data)}>
              {t('执行')}
            </auth-button>
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
              <auth-button
                theme="primary"
                text
                action-id="tendbcluster_partition_update"
                permission={data.permission.tendbcluster_partition_update}
                resource={data.cluster_id}
                disabled={data.isRunning}
                onClick={() => handleEdit(data)}>
                {t('编辑')}
              </auth-button>
            </span>
            <auth-button
              action-id="tendbcluster_partition"
              permission={data.permission.tendbcluster_partition}
              resource={data.cluster_id}
              class="ml-8 mr-8"
              theme="primary"
              text
              onClick={() => handleShowExecuteLog(data)}>
              {t('执行记录')}
            </auth-button>
            <more-action-extend>
              {{
                default: () => (
                  <>
                    {
                      data.isOnline && (
                        <bk-dropdown-item>
                          <auth-template
                            text
                            action-id="tendb_partition_enable_disable"
                            permission={data.permission.tendb_partition_enable_disable}
                            resource={data.cluster_id}>
                            <div onClick={() => handleDisable(data)}>{ t('禁用') }</div>
                          </auth-template>
                        </bk-dropdown-item>
                      )
                    }
                    <bk-dropdown-item>
                      <auth-template
                        text
                        action-id="tendbcluster_partition_create"
                        permission={data.permission.tendbcluster_partition_create}
                        resource={data.cluster_id}>
                        <div onClick={() => handleClone(data)}>{ t('克隆') }</div>
                      </auth-template>
                    </bk-dropdown-item>
                    <bk-dropdown-item>
                      <auth-template
                        action-id="tendbcluster_partition_delete"
                        permission={data.permission.tendbcluster_partition_delete}
                        resource={data.cluster_id}>
                        <db-popconfirm
                          confirm-handler={() => handleRemove(data)}
                          content={t('删除操作无法撤回，请谨慎操作！')}
                          title={t('确认删除该分区策略？')}>
                          <div>{ t('删除') }</div>
                        </db-popconfirm>
                      </auth-template>
                    </bk-dropdown-item>
                  </>
                ),
              }}
            </more-action-extend>
          </>
        );
      },
    },
  ];

  watch(searchValues, () => {
    tableRef.value!.clearSelected();
  });

  const getRowClass = (data: PartitionModel) => {
    const classList: string[] = [];
    if (data.isOffline) {
      classList.push('is-offline');
    }
    if (data.isNew) {
      classList.push('is-new-row');
    }
    return classList.join(' ');
  };

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

  const handleTableSelection = (payload: string[]) => {
    selectionList.value = payload.map(item => Number(item));
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

  // 编辑成功
  const handleOperationEditSuccess = () => {
    fetchData();
  };
  // 新建成功
  const handleOperationCreateSuccess = (payload: ServiceReturnType<typeof dryRun>, clusterId: number) => {
    fetchData();
    operationDryRunDataClusterId.value = clusterId;
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
    .header-action {
      display: flex;
    }

    .more-action {
      display: flex;
      width: 32px;
      height: 32px;
      font-size: 14px;
      cursor: pointer;
      border-radius: 50%;
      align-items: center;
      justify-content: center;

      &:hover {
        background: #dcdee5;
      }
    }

    .partition-table {
      .id-container {
        display: flex;
        align-items: center;
      }
    }
  }
</style>
