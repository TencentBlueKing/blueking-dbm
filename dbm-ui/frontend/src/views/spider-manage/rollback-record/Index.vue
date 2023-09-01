<template>
  <BkAlert
    closable
    theme="info"
    :title="$t('构造实例：通过定点构造产生的实例，可以将实例数据写回原集群或者直接销毁')" />
  <div class="mt-16 mb-16">
    <BkButton
      :disabled="selectionList.length < 1"
      @click="handleBatchDisable">
      {{ t('批量禁用') }}
    </BkButton>
  </div>
  <DbTable
    ref="tableRef"
    :columns="tableColumns"
    :data-source="queryFixpointLog"
    primary-key="target_cluster.cluster_id"
    selectable
    @selection="handleSelectionChange" />
</template>
<script setup lang="tsx">
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryFixpointLog } from '@services/fixpointRollback';
  import FixpointLogModel from '@services/model/fixpoint-rollback/fixpoint-log';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const tableRef = ref();
  const isBatchDisable = ref(false);
  const selectionList = ref<string[]>([]);

  const tableColumns = [
    {
      label: t('源集群'),
      width: 200,
      render: ({ data }: {data: FixpointLogModel}) => data.source_cluster.immute_domain,
    },
    {
      label: t('构造主机'),
      minWidth: 200,
      render: ({ data }: {data: FixpointLogModel}) => data.ipText || '--',
    },
    {
      label: t('回档类型'),
      minWidth: 200,
      render: ({ data }: {data: FixpointLogModel}) => data.rollbackTypeText,
    },
    {
      label: t('构造 DB 名'),
      minWidth: 100,
      render: ({ data }: {data: FixpointLogModel}) => (data.databases.length < 1 ? '--' : (
        <>
          {
            data.databases.map(item => (
              <bk-tag>{item}</bk-tag>
            ))
          }
        </>
      )),
    },
    {
      label: t('忽略 DB 名'),
      minWidth: 100,
      render: ({ data }: {data: FixpointLogModel}) => (data.databases_ignore.length < 1 ? '--' : (
        <>
          {
            data.databases_ignore.map(item => (
              <bk-tag>{item}</bk-tag>
            ))
          }
        </>
      )),
    },
    {
      label: t('构造表名'),
      minWidth: 100,
      render: ({ data }: {data: FixpointLogModel}) => (data.tables.length < 1 ? '--' : (
        <>
          {
            data.tables.map(item => (
              <bk-tag>{item}</bk-tag>
            ))
          }
        </>
      )),
    },
    {
      label: t('构造表名'),
      minWidth: 100,
      render: ({ data }: {data: FixpointLogModel}) => (data.tables_ignore.length < 1 ? '--' : (
        <>
          {
            data.tables_ignore.map(item => (
              <bk-tag>{item}</bk-tag>
            ))
          }
        </>
      )),
    },
    {
      label: t('关联单据'),
      width: 90,
      render: ({ data }: {data: FixpointLogModel}) => (
        <router-link
          to={{
            name: 'SelfServiceMyTickets',
            query: {
              filterId: data.ticket_id,
            },
          }}
          target="_blank">
          {data.ticket_id}
        </router-link>
      ),
    },
    {
      label: t('操作'),
      width: 100,
      fixed: 'right',
      render: ({ data }: {data: FixpointLogModel}) => (
        <bk-button
          theme="primary"
          text
          onClick={() => handleDestroy(data)}>
          {t('销毁')}
        </bk-button>
      ),
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData();
  };

  const handleDestroy = (payload: FixpointLogModel) => {
    createTicket({
      bk_biz_id: currentBizId,
      remark: '',
      ticket_type: 'TENDBCLUSTER_TEMPORARY_DESTROY',
      details: {
        cluster_ids: [payload.target_cluster.cluster_id],
      },
    }).then((data) => {
      ticketMessage(data.id);
      fetchData();
    });
  };

  const handleSelectionChange = (payload: string[]) => {
    selectionList.value = payload;
  };

  const handleBatchDisable = () => {
    isBatchDisable.value = true;
    createTicket({
      bk_biz_id: currentBizId,
      remark: '',
      ticket_type: 'TENDBCLUSTER_TEMPORARY_DESTROY',
      details: {
        cluster_ids: selectionList.value,
      },
    })
      .then((data) => {
        ticketMessage(data.id);
        fetchData();
      })
      .finally(() => {
        isBatchDisable.value = false;
      });
  };

  onMounted(() => {
    fetchData();
  });
</script>
