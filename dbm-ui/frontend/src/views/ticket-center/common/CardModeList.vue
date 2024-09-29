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
              'is-active': selectTicketId === ticketData.id,
            }"
            @click="handleClick(ticketData)">
            <div class="ticket-type">
              [{{ ticketData.id }}] {{ ticketData.ticket_type_display }}
              <TicketStatusTag
                class="ticket-status-tag"
                :data="ticketData"
                small />
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
  import { onActivated, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import { useEventBus, useStretchLayout, useUrlSearch } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

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

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { getSearchParams } = useUrlSearch();
  const eventBus = useEventBus();
  const { splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const { formatValue: formatDateValue } = useDatePicker();
  const { formatSearchValue } = useSearchSelect();

  const rootRef = useTemplateRef<HTMLElement>('root');
  const scrollFakerRef = useTemplateRef('scrollFaker');

  const selectTicketId = computed(() => Number(route.params.ticketId) || 0);

  const currentTicketScrollToTop = () => {
    setTimeout(() => {
      if (!rootRef.value) {
        return;
      }
      const activeItem = rootRef.value!.querySelector('.is-active');
      if (activeItem) {
        activeItem.scrollIntoView({
          block: 'start',
          behavior: 'smooth',
        });
      } else {
        scrollFakerRef.value?.scrollTo(0, 0);
      }
    }, 100);
  };

  const {
    loading: isLoading,
    pagination,
    fetchTicketList,
    dataList,
  } = usefetchData(props.dataSource, {
    onSuccess() {
      currentTicketScrollToTop();
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

  let isInit = true;

  const { pause: pauseFetchData, resume: resumeFetchData } = watch(
    [formatDateValue, formatSearchValue],
    _.debounce(() => {
      if (!isInit) {
        pagination.current = 1;
      }
      isInit = false;

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
    if (pageValue === pagination.current) {
      return;
    }
    pagination.current = pageValue;
    fetchData();
  };

  const handleClick = (data: TicketModel) => {
    router.replace({
      params: {
        ticketId: data.id,
      },
      query: getSearchParams(),
    });
  };

  onActivated(() => {
    resumeFetchData();
    currentTicketScrollToTop();
    eventBus.on('refreshTicketStatus', fetchData);
  });

  onDeactivated(() => {
    pauseFetchData();
    eventBus.off('refreshTicketStatus', fetchData);
  });

  onMounted(() => {
    stretchLayoutSplitScreen();
  });

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
        margin-top: 8px;

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
