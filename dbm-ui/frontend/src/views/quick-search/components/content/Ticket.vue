<template>
  <div>
    <DbCard
      class="search-result-ticket search-result-card"
      mode="collapse"
      :title="t('单据')">
      <template #desc>
        <I18nT
          class="ml-8"
          keypath="共n条"
          style="color: #63656e"
          tag="span">
          <template #n>
            <strong>{{ count }}</strong>
          </template>
        </I18nT>
      </template>
      <DbTable
        ref="table"
        class="mt-14"
        :data-source="dataSource"
        row-key="id"
        @clear-search="handleClearSearch"
        @request-success="handleReqestSuccess">
        <TableColumn
          col-key="id"
          :title="t('单号')"
          :width="150">
          <template #default="{ row }: { row: TicketModel }">
            <BkButton
              text
              theme="primary"
              @click="handleToTicket(row)">
              <TextHighlight
                high-light-color="#FF9C01"
                :keyword="keyword"
                :text="String(row.id)" />
            </BkButton>
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_type_display"
          :title="t('单据类型')">
          <template #default="{ row }: { row: TicketModel }">
            {{ row.ticket_type_display || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :title="t('单据状态')">
          <template #default="{ row }: { row: TicketModel }">
            <TicketStatusTag :data="row" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_biz_id"
          :title="t('业务')">
          <template #default="{ row }: { row: TicketModel }">
            {{ bizIdNameMap[row.bk_biz_id] || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="creator"
          :title="t('申请人')">
          <template #default="{ row }: { row: TicketModel }">
            {{ row.creator || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="create_at"
          :title="t('申请时间')">
          <template #default="{ row }: { row: TicketModel }">
            {{ row.createAtDisplay || '--' }}
          </template>
        </TableColumn>
      </DbTable>
    </DbCard>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { quickSearchResult } from '@services/source/quickSearch';

  import { useLocation } from '@hooks';

  import { batchSplitRegex } from '@common/regex';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    formData: {
      bk_biz_ids: number[];
      db_types: string[];
      filter_type: string;
      resource_types: string[];
    };
    keyword: string;
  }

  type Emits = (e: 'clear-search') => void;

  interface Exposed {
    fetchData: () => void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const location = useLocation();

  const tableRef = useTemplateRef('table');

  const count = ref(0);

  const fetchData = () => {
    if (props.formData.resource_types.length > 0 && !props.formData.resource_types.includes('ticket')) {
      return;
    }
    tableRef.value?.fetchData();
  };

  // watch(
  //   () => props.keyword,
  //   () => {
  //     fetchData();
  //   },
  // );

  const dataSource = (params: ServiceParameters<typeof quickSearchResult>) => {
    return quickSearchResult({
      ...params,
      ...props.formData,
      keyword: props.keyword.replace(batchSplitRegex, ' '),
      resource_type: 'ticket',
    });
  };

  const handleReqestSuccess = (data: ServiceReturnType<typeof quickSearchResult>) => {
    count.value = data.count;
  };

  const handleToTicket = (data: TicketModel) => {
    location(
      {
        name: 'bizTicketManage',
        params: {
          ticketId: data.id,
        },
      },
      data.bk_biz_id,
    );
  };

  const handleClearSearch = () => {
    emits('clear-search');
  };

  // onMounted(() => {
  //   fetchData();
  // });

  onActivated(() => {
    fetchData();
  });

  defineExpose<Exposed>({
    fetchData,
  });
</script>

<style lang="less" scoped>
  @import './table-card.less';
</style>
