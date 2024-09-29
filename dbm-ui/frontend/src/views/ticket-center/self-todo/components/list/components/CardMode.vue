<template>
  <div
    ref="root"
    class="ticket-list-card-mode">
    <div class="action-box">
      <BkSelect
        v-model="ticketType"
        class="mb-16">
        <template #trigger="{ selected }">
          <div class="ticket-status-box">
            <div>{{ selected[0]?.label }}</div>
            <DbIcon
              style="margin-left: auto; font-size: 12px"
              type="down-shape" />
          </div>
        </template>
        <BkOption
          :id="TicketModel.STATUS_TODO"
          :name="`${t('待审批')}(${ticketCount?.TODO ?? 0})`" />
        <BkOption
          :id="TicketModel.STATUS_APPROVE"
          :name="`${t('待执行')}(${ticketCount?.APPROVE})`" />
        <BkOption
          :id="TicketModel.STATUS_RESOURCE_REPLENISH"
          :name="`${t('待补货')}(${ticketCount?.RESOURCE_REPLENISH})`" />
        <BkOption
          :id="TicketModel.STATUS_FAILED"
          :name="`${t('失败待处理')}(${ticketCount?.FAILED})`" />
        <BkOption
          :id="TicketModel.STATUS_RUNNING"
          :name="`${t('待确认')}(${ticketCount?.RUNNING})`" />
      </BkSelect>
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
    <div style="height: calc(100% - 160px)">
      <CardModeList
        ref="list"
        v-model="modelValue"
        :data-source="dataSource" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import { useTicketCount, useUrlSearch } from '@hooks';

  import CardModeList from '@views/ticket-center/common/CardModeList.vue';
  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';

  const { t } = useI18n();

  const route = useRoute();
  const router = useRouter();

  const { data: ticketCount } = useTicketCount();
  const { appendSearchParams } = useUrlSearch();
  const { value: datePickerValue, shortcutsRange } = useDatePicker();
  const { value: searachSelectValue, searchSelectData } = useSearchSelect();

  const modelValue = defineModel<number>();

  const dataTableRef = useTemplateRef('list');

  const ticketType = ref((route.params.status as string) || TicketModel.STATUS_TODO);

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      todo: 'running',
      self_manage: 1,
      status: ticketType.value,
    });

  watch(ticketType, () => {
    dataTableRef.value!.fetchData();
    router.replace({
      params: {
        status: ticketType.value,
      },
    });
  });

  watch(modelValue, () => {
    appendSearchParams({
      viewId: modelValue.value,
    });
  });

  onActivated(() => {
    ticketType.value = (route.params.status as string) || TicketModel.STATUS_TODO;
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

    .ticket-status-box {
      display: flex;
      height: 32px;
      padding: 0 16px;
      font-size: 14px;
      color: #63656e;
      cursor: pointer;
      background: #f0f1f5;
      align-items: center;
    }

    .action-box {
      padding: 16px 24px;
    }
  }
</style>
