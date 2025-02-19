<template>
  <BkAlert
    closable
    theme="info"
    :title="$t('构造实例：通过定点构造产生的实例，可以将实例数据写回原集群或者直接销毁')" />
  <div class="mt-16 mb-16">
    <DbPopconfirm
      :confirm-handler="handleBatchDisable"
      :content="t('移除后将不可恢复')"
      :title="t('确认销毁选中的实例')">
      <BkButton :disabled="selectionList.length < 1">
        {{ t('批量销毁') }}
      </BkButton>
    </DbPopconfirm>
  </div>
  <DbTable
    ref="tableRef"
    :columns="tableColumns"
    :data-source="queryFixpointLog"
    :disable-select-method="disableSelectMethodCallback"
    primary-key="target_cluster.cluster_id"
    selectable
    @selection="handleSelectionChange" />
</template>
<script setup lang="tsx">
  import { onMounted, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FixpointLogModel from '@services/model/fixpoint-rollback/fixpoint-log';
  import { queryFixpointLog } from '@services/source/fixpointRollback';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const tableRef = ref();
  const selectionList = ref<string[]>([]);

  const tableColumns = [
    {
      label: t('源集群'),
      render: ({ data }: { data: FixpointLogModel }) => data.source_cluster.immute_domain,
      showOverflowTooltip: true,
      width: 200,
    },
    {
      label: t('构造主机'),
      minWidth: 200,
      render: ({ data }: { data: FixpointLogModel }) => data.ipText || '--',
      showOverflowTooltip: true,
    },
    {
      label: t('回档类型'),
      minWidth: 200,
      render: ({ data }: { data: FixpointLogModel }) => data.rollbackTypeText,
      showOverflowTooltip: true,
    },
    {
      label: t('构造 DB 名'),
      minWidth: 100,
      render: ({ data }: { data: FixpointLogModel }) =>
        data.databases.length < 1 ? (
          '--'
        ) : (
          <>
            {data.databases.map((item) => (
              <bk-tag>{item}</bk-tag>
            ))}
          </>
        ),
      showOverflowTooltip: true,
    },
    {
      label: t('忽略 DB 名'),
      minWidth: 100,
      render: ({ data }: { data: FixpointLogModel }) =>
        data.databases_ignore.length < 1 ? (
          '--'
        ) : (
          <>
            {data.databases_ignore.map((item) => (
              <bk-tag>{item}</bk-tag>
            ))}
          </>
        ),
      showOverflowTooltip: true,
    },
    {
      label: t('构造表名'),
      minWidth: 100,
      render: ({ data }: { data: FixpointLogModel }) =>
        data.tables.length < 1 ? (
          '--'
        ) : (
          <>
            {data.tables.map((item) => (
              <bk-tag>{item}</bk-tag>
            ))}
          </>
        ),
      showOverflowTooltip: true,
    },
    {
      label: t('忽略表名'),
      minWidth: 100,
      render: ({ data }: { data: FixpointLogModel }) =>
        data.tables_ignore.length < 1 ? (
          '--'
        ) : (
          <>
            {data.tables_ignore.map((item) => (
              <bk-tag>{item}</bk-tag>
            ))}
          </>
        ),
      showOverflowTooltip: true,
    },
    {
      label: t('关联单据'),
      render: ({ data }: { data: FixpointLogModel }) => (
        <router-link
          to={{
            name: 'bizTicketManage',
            params: {
              ticketId: data.ticket_id,
            },
          }}
          target='_blank'>
          {data.ticket_id}
        </router-link>
      ),
      showOverflowTooltip: true,
      width: 90,
    },
    {
      fixed: 'right',
      label: t('操作'),
      render: ({ data }: { data: FixpointLogModel }) => (
        <db-popconfirm
          confirm-handler={() => handleDestroy(data)}
          content={t('移除后将不可恢复')}
          title={t('确认销毁选中的实例')}>
          <bk-button
            disabled={!data.isDestoryEnable}
            theme='primary'
            text>
            {t('销毁')}
          </bk-button>
        </db-popconfirm>
      ),
      width: 100,
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData();
  };

  const disableSelectMethodCallback = (data: FixpointLogModel) => !data.isDestoryEnable;

  const handleDestroy = (payload: FixpointLogModel) =>
    createTicket({
      bk_biz_id: currentBizId,
      details: {
        cluster_ids: [payload.target_cluster.cluster_id],
      },
      remark: '',
      ticket_type: TicketTypes.TENDBCLUSTER_TEMPORARY_DESTROY,
    }).then((data) => {
      ticketMessage(data.id);
      fetchData();
    });

  const handleSelectionChange = (payload: string[]) => {
    selectionList.value = payload;
  };

  const handleBatchDisable = () =>
    createTicket({
      bk_biz_id: currentBizId,
      details: {
        cluster_ids: selectionList.value,
      },
      remark: '',
      ticket_type: TicketTypes.TENDBCLUSTER_TEMPORARY_DESTROY,
    }).then((data) => {
      ticketMessage(data.id);
      fetchData();
    });

  onMounted(() => {
    fetchData();
  });
</script>
