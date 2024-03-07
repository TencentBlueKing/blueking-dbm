<template>
  <div>
    <BkAlert
      closable
      theme="info"
      :title="t('数据迁移：数据同步复制到新集群')" />
    <BkInput
      v-model="searchKeyword"
      :placeholder="t('请输入集群名称')"
      style="width: 500px; margin-top: 16px"
      @change="handelChange" />
    <BkLoading :loading="isLoading">
      <BkTable
        class="mt-16"
        :columns="tableColumns"
        :data="data" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import {ref} from 'vue'
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MigrateRecordModel from '@services/model/sqlserver/migrate-record';
  import { forceFailedMigrate, getList, manualTerminateSync } from '@services/source/sqlServerMigrate';

  import { messageSuccess } from '@utils'

  const { t } = useI18n();

  const searchKeyword = ref('');

  const tableColumns = [
    {
      label: t('源集群'),
      width: 180,
      fixed: 'left',
      field: 'source_cluster_domain',
    },
    {
      label: t('目标集群'),
      width: 180,
      fixed: 'left',
      field: 'target_cluster_domain',
    },
    {
      label: t('迁移类型'),
      width: 180,
    },
    {
      label: t('迁移 DB'),
      width: 180,
      render: ({data}: {data: MigrateRecordModel}) => (
        <>
          {data.tagetDb.map(item => <bk-tag>{item}</bk-tag>)}
        </>
      )
    },
    {
      label: t('忽略 DB'),
      width: 180,
      render: ({data}: {data: MigrateRecordModel}) => (
        <>
          {data.ignore_db_list.length < 1 ? '--':data.ignore_db_list.map(item => <bk-tag>{item}</bk-tag>)}
        </>
      )
    },
    {
      label: t('关联单据'),
      minWidth: 120,
      render: ({data}: {data: MigrateRecordModel}) => {
        if (!data.ticket_id) {
          return '--'
        }
        return (
          <router-link
            to={{
              name: 'bizTicketManage',
              query: {
                id: data.ticket_id
              }

            }}
            target='_blank'>
            {data.ticket_id}
          </router-link>
        )
      }
    },
    {
      label: t('状态'),
      minWidth: 120,
      render: ({data}: {data: MigrateRecordModel}) => (
        <>
          <span
            class={{ 'rotate-loading': data.isRunning}}
            style="display: inline-block; line-height: 0; vertical-align: middle;">
            <db-icon
              type={MigrateRecordModel.statusIconMap[data.status]}
              svg />
          </span>
          <span class="ml-4" style="vertical-align: middle;">
            {MigrateRecordModel.statusTextMap[data.status]}
          </span>
        </>
      )
    },
    {
      label: t('创建时间'),
      width: 250,
      render: ({data}: {data: MigrateRecordModel}) => data.createAtDisplay
    },
    {
      label: t('操作'),
      width: 150,
      fixed: 'right',
      render: ({data}: {data: MigrateRecordModel}) => (
        <>
          <bk-button
            theme="primary"
            text
            onClick={() => handleForcedTermination(data)}>
            {t('强制终止')}
          </bk-button>
          <bk-button
            theme="primary"
            text
            class="ml-8"
            onClick={() => handleStopSync(data)}>
            {t('断开同步')}
          </bk-button>
        </>
      )
    },
  ];

  const { loading: isLoading, data, run: fetchList } = useRequest(getList);

  const { run: runForceFailedMigrate } = useRequest(forceFailedMigrate, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'))
      fetchList({
        cluster_name: searchKeyword.value
      })
    }
  })
  const { run: runManualTerminateSynce } = useRequest(manualTerminateSync, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'))
      fetchList({
        cluster_name: searchKeyword.value
      })
    }
  })

  const handelChange = (value: string) => {
    fetchList({
      cluster_name: value
    })
  }

  const handleForcedTermination = (data: MigrateRecordModel) => {
    runForceFailedMigrate({
      dts_id: data.id
    })
  }

  const handleStopSync = (data: MigrateRecordModel) => {
    runManualTerminateSynce({
      ticket_id: data.ticket_id
    })
  }
</script>
