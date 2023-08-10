<template>
  <div class="spider-manage-paritition-page">
    <div class="header-action mb-16">
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleCreate">
        {{ t('新建') }}
      </BkButton>
      <BkButton
        class="ml-8"
        :disabled="selectionList.length < 1"
        @click="handleBatchRemove">
        {{ t('删除') }}
      </BkButton>
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
      selectable
      @selection="handleTableSelection" />
    <DbSideslider
      v-model:is-show="isShowOperation"
      :title="Boolean(operationData) ? t('编辑分区策略') : t('新建分区策略')"
      :width="1000">
      <PartitionOperation :data="operationData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowExecuteLog"
      :title="t(`策略执行详情`)"
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
    dryRun,
    execute as executePartition,
    getList,
  } from '@services/partitionManage';

  import { ClusterTypes } from '@common/const';

  import {
    getSearchSelectorParams,
    messageSuccess,
  } from '@utils';

  import ExecuteLog from './components/ExecuteLog.vue';
  import PartitionOperation from './components/Operation.vue';

  const { t } = useI18n();

  const tableRef = ref();
  const searchValues = ref([]);
  const isShowOperation = ref(false);
  const isShowExecuteLog = ref(false);
  const executeLoadingMap = ref<Record<number, boolean>>({});
  const selectionList = shallowRef<number[]>([]);
  const operationData = shallowRef<PartitionModel>();

  const serachData = [
    {
      name: t('域名'),
      id: 'immute_domain',
    },
    {
      name: t('DB 名'),
      id: 'dblike',
    },
    {
      name: t('表名'),
      id: 'tblike',
    },
    {
      name: '分区字段',
      id: 'partition_columns',
    },
  ];

  const tableColumn = [
    {
      label: t('策略 ID'),
      field: 'id',
      fixed: true,
    },
    {
      label: t('集群域名'),
      field: 'immute_domain',
      width: 240,
    },
    {
      label: t('DB 名'),
      field: 'dblike',
      width: 100,
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
      width: 100,
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
    },
    {
      label: t('最近一次执行时间'),
      field: 'execute_time',
      minWidth: 180,
    },
    {
      label: t('连续失败天数'),
      field: 'extra_partition',
      minWidth: 150,
    },
    {
      label: t('操作'),
      field: 'action',
      minWidth: 150,
      fixed: 'right',
      render: ({ data }: { data: PartitionModel }) => (
        <>
          <bk-button
            theme="primary"
            text
            loading={executeLoadingMap.value[data.id]}
            onClick={() => handleExecute(data)}>
            {t('执行')}
          </bk-button>
          <bk-button
            class="ml-8"
            theme="primary"
            text
            onClick={() => handleEdit(data)}>
            {t('编辑')}
          </bk-button>
          <bk-button
            class="ml-8"
            theme="primary"
            text
            onClick={() => handleShowExecuteLog(data)}>
            {t('执行记录')}
          </bk-button>
        </>
      ),
    },
  ];

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    tableRef.value?.fetchData(searchParams, {
      cluster_type: ClusterTypes.SPIDER,
    });
  };

  const handleCreate = () => {
    isShowOperation.value = true;
  };

  // 批量删除
  const handleBatchRemove = () => {
    batchRemove({
      cluster_type: ClusterTypes.SPIDER,
      ids: selectionList.value,
    });
  };

  // 搜索
  const handleSearch = () => {
    fetchData();
  };

  const handleTableSelection = (payload: number[]) => {
    selectionList.value = payload;
  };

  // 执行
  const handleExecute = (payload: PartitionModel) => {
    executeLoadingMap.value[payload.id] = true;
    dryRun({
      config_id: payload.id,
      cluster_id: payload.cluster_id,
      cluster_type: ClusterTypes.SPIDER,
    })
      .then(data => executePartition({
        cluster_id: payload.cluster_id,
        partition_objects: data,
      }))
      .then(() => {
        messageSuccess(t('执行成功'));
        fetchData();
      })
      .finally(() => {
        executeLoadingMap.value[payload.id] = false;
      });
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
  };
</script>
<style lang="postcss">
  .spider-manage-paritition-page {
    .header-action{
      display: flex;
    }
  }
</style>
