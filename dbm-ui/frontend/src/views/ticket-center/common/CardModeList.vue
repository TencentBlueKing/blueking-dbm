<template>
  <div
    ref="root"
    class="card-mode-ticket-list">
    <template v-if="dataList.length > 0">
      <ScrollFaker
        ref="scrollFaker"
        style="height: calc(100% - 53px)">
        <BkLoading :loading="isLoading">
          <div
            v-for="ticketData in dataList"
            :key="ticketData.id"
            class="ticket-item-box"
            :class="{
              'is-active': modelValue === ticketData.id,
            }"
            @click="handleClick(ticketData)">
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
    </template>
    <EmptyStatus
      v-else
      :is-anomalies="false"
      :is-searching="isSearching" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';

  import useDatePicker from './hooks/use-date-picker';
  import usefetchData from './hooks/use-fetch-data';
  import useSearchSelect from './hooks/use-search-select';

  interface Props {
    dataSource: typeof getTickets;
  }

  interface Exposes {
    fetchData: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { formatValue: formatDateValue } = useDatePicker();
  const { formatSearchValue } = useSearchSelect();

  let isInited = false;

  const modelValue = defineModel<number>();

  const rootRef = useTemplateRef<HTMLElement>('root');
  const scrollFakerRef = useTemplateRef('scrollFaker');

  const {
    loading: isLoading,
    pagination,
    fetchTicketList,
    dataList,
  } = usefetchData(props.dataSource, {
    onSuccess(data) {
      console.log('datatat = ', data);
      if (!modelValue.value && data.length > 0) {
        handleClick(data[0]);
      }
      nextTick(() => {
        const activeItem = rootRef.value!.querySelector('.is-active');
        if (activeItem) {
          activeItem.scrollIntoView({
            block: 'center',
          });
        } else {
          scrollFakerRef.value!.scrollTo(0, 0);
        }
      });
    },
  });

  const isSearching = computed(
    () =>
      Object.keys(formatSearchValue.value).length > 0 ||
      formatDateValue.value.create_at__gte !== '' ||
      formatDateValue.value.create_at__lte !== '',
  );

  const fetchData = () => {
    fetchTicketList({
      ...formatDateValue.value,
      ...formatSearchValue.value,
    });
  };

  watch(
    [formatDateValue, formatSearchValue],
    _.debounce(() => {
      if (!isInited) {
        isInited = true;
        return;
      }
      pagination.current = 1;

      fetchData();
    }, 100),
  );

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

  const handleClick = (data: TicketModel<unknown>) => {
    modelValue.value = data.id;
  };

  defineExpose<Exposes>({
    fetchData,
  });
</script>
<style lang="less">
  .card-mode-ticket-list {
    height: 100%;

    .ticket-item-box {
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
