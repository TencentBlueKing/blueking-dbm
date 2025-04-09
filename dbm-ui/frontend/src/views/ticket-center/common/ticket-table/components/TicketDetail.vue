<template>
  <div
    v-bk-loading="{ isLoading: isLoading }"
    class="table-ticket-detail-box">
    <PermissionCatch>
      <div
        v-if="ticketData"
        class="ticket-detail-info">
        <div class="row-title">
          <div class="ticket-type">{{ ticketData?.ticket_type_display }}</div>
          <TicketStatusTag
            class="ml-8"
            :data="ticketData"
            small />
          <BkDropdown placement="bottom-start">
            <BkButton
              v-bk-tooltips="t('复制')"
              class="ml-8"
              size="small"
              style="padding: 0 8px">
              <DbIcon type="copy-2" />
            </BkButton>
            <template #content>
              <BkDropdownItem @click="handleCopyLink">{{ t('单据链接') }}</BkDropdownItem>
              <BkDropdownItem @click="handleCopyTitleAndLink">{{ t('标题 + 单据链接') }}</BkDropdownItem>
            </template>
          </BkDropdown>
          <RouterLink
            class="go-detail-btn"
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: ticketId,
              },
            }">
            <DbIcon
              class="mr-4"
              type="link" />
            {{ t('新窗口打开') }}
          </RouterLink>
        </div>
        <div class="row-info">
          <div class="info-item">
            {{ t('单号：') }}
            <span class="value">{{ ticketData.id }}</span>
          </div>
          <div class="info-item">
            {{ t('业务：') }}
            <span class="value">{{ ticketData.bk_biz_name }}</span>
          </div>
          <div class="info-item">
            {{ t('申请人：') }}
            <span class="value">{{ ticketData.creator }}</span>
          </div>
          <div class="info-item">
            {{ t('申请时间：') }}
            <span class="value">{{ ticketData.createAtDisplay }}</span>
          </div>
          <div class="info-item">
            {{ t('已耗时：') }}
            <CostTimer
              class="value"
              :is-timing="ticketData.status === 'RUNNING'"
              :start-time="utcTimeToSeconds(ticketData.create_at)"
              :value="ticketData.cost_time || 0" />
          </div>
        </div>
      </div>
      <div class="ticket-more">
        <TicketDetail
          v-if="ticketId"
          smart-action-teleport-to=".dbm-table-detail-dialog-content"
          :ticket-id="ticketId" />
      </div>
    </PermissionCatch>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketDetails, getTicketStatus } from '@services/source/ticket';

  import PermissionCatch from '@components/apply-permission/Catch.vue';
  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import TicketDetail from '@views/ticket-center/common/ticket-detail/Index.vue';

  import { execCopy, getSelfDomain, utcTimeToSeconds } from '@utils';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    ticketId?: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const isLoading = ref(true);
  const ticketData = shallowRef<TicketModel>();

  const { runAsync: fetchTicketDetails } = useRequest(
    (params: ServiceParameters<typeof getTicketDetails>) =>
      getTicketDetails(params, {
        cache: 1000,
        permission: 'catch',
      }),
    {
      manual: true,
      onSuccess(data) {
        ticketData.value = data;
      },
    },
  );

  const { refresh: refreshTicketStatus } = useRequest(
    () => {
      return getTicketStatus({
        ticket_ids: `${props.ticketId}`,
      });
    },
    {
      manual: true,
      onSuccess(data) {
        if (ticketData.value) {
          Object.assign(ticketData.value, {
            status: data[ticketData.value.id] as string,
          });
          if (!ticketData.value.isFinished) {
            loopFetchTicketStatus();
          }
        }
      },
    },
  );

  const { start: loopFetchTicketStatus } = useTimeoutFn(() => {
    refreshTicketStatus();
  }, 3000);

  watch(
    () => props.ticketId,
    () => {
      if (props.ticketId) {
        isLoading.value = true;
        ticketData.value = undefined;
        fetchTicketDetails({
          id: props.ticketId,
        }).finally(() => {
          isLoading.value = false;
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleCopyLink = () => {
    const { href } = router.resolve({
      name: 'ticketDetail',
      params: {
        ticketId: props.ticketId,
      },
      query: {
        test: 1,
      },
    });
    execCopy(`${getSelfDomain()}${href}`);
  };

  const handleCopyTitleAndLink = () => {
    const { href } = router.resolve({
      name: 'ticketDetail',
      params: {
        ticketId: props.ticketId,
      },
    });

    execCopy(`${ticketData.value?.ticket_type_display}\n${getSelfDomain()}${href}`);
  };
</script>
<style lang="less">
  .table-ticket-detail-box {
    position: relative;
    display: flex;
    height: 100%;
    overflow: hidden;
    flex-direction: column;

    .ticket-detail-info {
      padding: 12px 24px;
      background: #f0f1f5;

      .row-title {
        display: flex;
        padding-top: 3px;
        padding-right: 40px;
        align-items: center;

        .ticket-type {
          overflow: hidden;
          font-size: 16px;
          font-weight: 700;
          line-height: 24px;
          letter-spacing: 0;
          color: #313238;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      .row-info {
        display: flex;
        margin-top: 4px;
        font-size: 12px;
        line-height: 20px;
        color: #979ba5;
        white-space: nowrap;
        flex-wrap: wrap;

        .info-item {
          margin-right: 40px;
        }

        .value {
          color: #313238;
        }
      }
    }

    .go-detail-btn {
      margin-left: auto;
      font-size: 12px;
    }

    .ticket-more {
      padding: 0 24px;
      overflow: hidden;
      flex: 1;
      background: #f0f1f5;
    }
  }
</style>
