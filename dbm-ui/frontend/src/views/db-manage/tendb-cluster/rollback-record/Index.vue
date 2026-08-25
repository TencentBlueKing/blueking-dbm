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
    :data-source="queryFixpointLog"
    :disable-select-method="disableSelectMethodCallback"
    row-key="target_cluster.cluster_id"
    selectable
    @selection="handleSelectionChange">
    <TableColumn
      col-key="source_cluster"
      :title="t('源集群')"
      :width="200">
      <template #default="{ row }: { row: FixpointLogModel }">
        {{ row.source_cluster.immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="ip"
      :min-width="200"
      :title="t('构造主机')">
      <template #default="{ row }: { row: FixpointLogModel }">
        {{ row.ipText || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="rollback_type"
      :min-width="200"
      :title="t('回档类型')">
      <template #default="{ row }: { row: FixpointLogModel }">
        {{ row.rollbackTypeText }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="databases"
      :min-width="100"
      :title="t('构造 DB 名')">
      <template #default="{ row }: { row: FixpointLogModel }">
        <template v-if="row.databases.length > 0">
          <BkTag
            v-for="item in row.databases"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <span v-else>--</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="databases_ignore"
      :min-width="100"
      :title="t('忽略 DB 名')">
      <template #default="{ row }: { row: FixpointLogModel }">
        <template v-if="row.databases_ignore.length > 0">
          <BkTag
            v-for="item in row.databases_ignore"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <span v-else>--</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="tables"
      :min-width="100"
      :title="t('构造表名')">
      <template #default="{ row }: { row: FixpointLogModel }">
        <template v-if="row.tables.length > 0">
          <BkTag
            v-for="item in row.tables"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <span v-else>--</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="tables_ignore"
      :min-width="100"
      :title="t('忽略表名')">
      <template #default="{ row }: { row: FixpointLogModel }">
        <template v-if="row.tables_ignore.length > 0">
          <BkTag
            v-for="item in row.tables_ignore"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <span v-else>--</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="ticket_id"
      :title="t('关联单据')"
      :width="90">
      <template #default="{ row }: { row: FixpointLogModel }">
        <RouterLink
          target="_blank"
          :to="{
            name: 'bizTicketManage',
            params: {
              ticketId: row.ticket_id,
            },
          }">
          {{ row.ticket_id }}
        </RouterLink>
      </template>
    </TableColumn>
    <TableColumn
      col-key="operation"
      fixed="right"
      :title="t('操作')"
      :width="100">
      <template #default="{ row }: { row: FixpointLogModel }">
        <DbPopconfirm
          :confirm-handler="() => handleDestroy(row)"
          :content="t('移除后将不可恢复')"
          :title="t('确认销毁选中的实例')">
          <BkButton
            :disabled="!row.isDestoryEnable"
            text
            theme="primary">
            {{ t('销毁') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </TableColumn>
  </DbTable>
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

  import DbTable from '@components/db-table/IndexNew.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const tableRef = ref();
  const selectionList = ref<string[]>([]);

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

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
