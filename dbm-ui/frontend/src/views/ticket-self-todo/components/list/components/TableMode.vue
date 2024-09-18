<template>
  <div class="ticket-list-table-mode">
    <div class="header-action-box">
      <BkDatePicker
        v-model="datePickerValue"
        format="yyyy-MM-dd HH:mm:ss"
        :shortcuts="shortcutsRange"
        style="margin-left: auto"
        type="datetimerange"
        use-shortcut-text />
      <DbSearchSelect
        v-model="searachSelectValue"
        :data="searchSelectData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 450px; margin-left: 16px"
        unique-select />
    </div>
    <div ref="table">
      <BkLoading :loading="isLoading">
        <BkTable
          :data="dataList"
          :max-height="tableMaxHeight"
          :pagination="pagination"
          remote-pagination
          :show-overflow-tooltip="{
            popoverOption: {
              maxWidth: 500,
            },
          }"
          @page-limit-change="handlePageLimitChange"
          @page-value-change="handlePageValueChange">
          <BkTableColumn
            field="id"
            :label="t('单据')"
            width="100">
            <template #default="{ data }: { data: IRowData }">
              <BkButton
                v-if="data"
                text
                theme="primary"
                @click="() => handleShowDetail(data)">
                {{ data.id }}
              </BkButton>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_biz_name"
            :label="t('业务')"
            :min-width="150" />
          <BkTableColumn
            field="ticket_type_display"
            :label="t('单据类型')"
            :min-width="200" />
          <BkTableColumn
            field="ticket_type_display"
            :label="t('集群')"
            min-width="250">
            <template #default="{ data }: { data: IRowData }">
              <MultLineText
                v-if="data.related_object.objects"
                :line="3"
                style="padding: 8px 0">
                <div
                  v-for="item in data.related_object.objects"
                  :key="item"
                  style="line-height: 20px">
                  {{ item }}
                </div>
              </MultLineText>
              <template v-else> -- </template>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="status"
            :label="t('状态')"
            :min-width="100">
            <template #default="{ data }: { data: IRowData }">
              <BkTag :theme="data.tagTheme">
                {{ data.statusText }}
              </BkTag>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="remark"
            :label="t('备注')">
            <template #default="{ data }: { data: IRowData }">
              {{ data.remark || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="creator"
            :label="t('申请人')"
            width="250" />
          <BkTableColumn
            field="createAtDisplay"
            :label="t('申请时间')"
            width="250" />
        </BkTable>
      </BkLoading>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { onMounted } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import { useStretchLayout, useUrlSearch } from '@hooks';

  import MultLineText from '@components/mult-line-text/Index.vue';

  import useData from './hooks/use-data';
  import useDatePicker from './hooks/use-date-picker';
  import useSearchSelect from './hooks/use-search-select';
  import useTableHeight from './hooks/use-table-height';

  type IRowData = TicketModel<unknown>;

  const route = useRoute();

  const { t } = useI18n();
  const { appendSearchParams, getSearchParams } = useUrlSearch();

  const { tableMaxHeight } = useTableHeight();
  const { splitScreen: stretchLayoutSplitScreen } = useStretchLayout();
  const { value: datePickerValue, shortcutsRange, formatValue: formatDateValue } = useDatePicker();
  const { loading: isLoading, pagination, fetchTicketList, dataList } = useData();
  const { value: searachSelectValue, searchSelectData, formatSearchValue } = useSearchSelect();

  const modelValue = defineModel<number>();

  const handleShowDetail = (data: IRowData) => {
    modelValue.value = data.id;
    stretchLayoutSplitScreen();
    appendSearchParams({
      viewId: data.id,
    });
  };

  const fetchData = () => {
    fetchTicketList({
      ...formatDateValue.value,
      ...formatSearchValue.value,
    });
  };

  watch([formatDateValue, formatSearchValue], () => {
    pagination.current = 1;
    fetchData();
  });

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    fetchData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    fetchData();
  };

  onMounted(() => {
    const searchParams = getSearchParams();
    if (Number(searchParams.viewId)) {
      modelValue.value = Number(route.query.viewId);
      stretchLayoutSplitScreen();
    }
  });
</script>
<style lang="less">
  .ticket-list-table-mode {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
