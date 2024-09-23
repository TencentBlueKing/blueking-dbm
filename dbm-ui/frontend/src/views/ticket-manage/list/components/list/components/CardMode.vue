<template>
  <div
    ref="root"
    class="ticket-list-card-mode">
    <div class="action-box">
      <BkDatePicker
        v-model="datePickerValue"
        format="yyyy-MM-dd HH:mm:ss"
        :shortcuts="shortcutsRange"
        style="width: 100%"
        type="datetimerange"
        use-shortcut-text />
      <DbSearchSelect
        v-model="searachSelectValue"
        :data="searchSelectData"
        :placeholder="t('请输入或选择条件搜索')"
        style="margin-top: 16px"
        unique-select />
    </div>
    <ScrollFaker style="height: calc(100% - 165px)">
      <BkLoading :loading="isLoading">
        <div
          v-for="ticketData in dataList"
          :key="ticketData.id"
          class="ticket-info-box"
          :class="{
            'is-active': modelValue === ticketData.id,
          }"
          @click="handleSelect(ticketData)">
          <div class="ticket-type">
            {{ ticketData.ticket_type_display }}
            <BkTag
              class="ticket-status-tag"
              size="small"
              :theme="ticketData.tagTheme">
              {{ ticketData.statusText }}
            </BkTag>
          </div>
          <div class="ticket-info-more">
            <div class="ticket-info-label">{{ t('集群') }}：</div>
            <RenderRow
              :data="ticketData.related_object.objects || []"
              show-all
              style="overflow: hidden" />
          </div>
          <div class="ticket-info-more">
            <div class="ticket-info-label">{{ t('业务') }}：</div>
            <div
              v-overflow-tips
              class="text-overflow">
              {{ ticketData.bk_biz_name }}
            </div>
          </div>
          <div class="ticket-info-more">
            <div>{{ t('申请人') }}： {{ ticketData.creator }}</div>
            <div style="margin-left: auto">{{ ticketData.createAtDisplay }}</div>
          </div>
        </div>
      </BkLoading>
    </ScrollFaker>
    <div class="data-pagination">
      <BkPagination
        align="center"
        class="side-pagination"
        :count="pagination.count"
        :limit="pagination.limit"
        :model-value="pagination.current"
        :show-total-count="false"
        small
        @change="handlePageValueChange"
        @limit-change="handlePageLimitChange" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { useUrlSearch } from '@hooks';

  import RenderRow from '@components/render-row/index.vue';

  import useData from './hooks/use-data';
  import useDatePicker from './hooks/use-date-picker';
  import useSearchSelect from './hooks/use-search-select';

  const { t } = useI18n();

  const modelValue = defineModel<number>();

  const rootRef = useTemplateRef('root');

  const { appendSearchParams } = useUrlSearch();
  const { value: datePickerValue, shortcutsRange, formatValue: formatDateValue } = useDatePicker();
  const { value: searachSelectValue, searchSelectData, formatSearchValue } = useSearchSelect();

  const handleSelect = (data: TicketModel<unknown>) => {
    modelValue.value = data.id;
    appendSearchParams({
      viewId: data.id,
    });
  };

  const {
    loading: isLoading,
    pagination,
    fetchTicketList,
    dataList,
  } = useData({
    onSuccess(data) {
      if (!modelValue.value && data.length > 0) {
        handleSelect(data[0]);
      }
      nextTick(() => {
        const activeItem = rootRef.value!.querySelector('.is-active');
        if (activeItem) {
          activeItem.scrollIntoView({
            block: 'center',
          });
        }
      });
    },
  });

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
    if (dataList.value.length < 1) {
      fetchData();
    }
  });

  onBeforeUnmount(() => {
    appendSearchParams({
      viewId: '',
    });
  });
</script>
<style lang="less">
  .ticket-list-card-mode {
    position: relative;
    z-index: 100;
    height: calc(100vh - var(--notice-height) - 104px);
    background: #fff;

    .scroll-faker {
      .scroll-faker-content {
        height: 100%;
      }
    }

    .action-box {
      padding: 16px 24px;
    }

    .ticket-info-box {
      padding: 16px 24px;
      font-size: 12px;
      line-height: 16px;
      color: #63656e;
      cursor: pointer;
      border-top: 1px solid #dcdee5;

      &:hover,
      &.is-active {
        background: #ebf2ff;
        transition: all 0.15s;
      }

      .ticket-type {
        font-weight: bold;
        color: #63656e;
      }

      .ticket-status-tag {
        flex-shrink: 0;
      }

      .ticket-info-more {
        display: flex;

        & ~ .ticket-info-more {
          margin-top: 8px;
        }

        .ticket-info-label {
          flex-shrink: 0;
        }

        .info-item-value {
          flex-grow: 1;

          :deep(.bk-tag) {
            height: 16px;
            padding: 0 4px;
            margin: 0;
            line-height: 16px;
          }
        }
      }
    }

    .data-pagination {
      display: flex;
      justify-content: center;
      padding: 13px 0;
      border-top: 1px solid #dcdee5;
    }
  }
</style>
