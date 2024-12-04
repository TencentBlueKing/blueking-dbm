<template>
  <div
    ref="root"
    class="ticket-list-card-mode">
    <div class="action-box">
      <BkSelect
        v-model="ticketStatus"
        class="mb-16">
        <template #trigger>
          <div class="ticket-status-box">
            <div>{{ ticektStatusName }}</div>
            <DbIcon
              style="margin-left: auto; font-size: 12px"
              type="down-shape" />
          </div>
        </template>
        <BkOption
          v-for="item in statusList"
          :id="item.id"
          :key="item.id"
          :name="item.name" />
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
        :data-source="dataSource" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getTickets } from '@services/source/ticket';

  import CardModeList from '@views/ticket-center/common/CardModeList.vue';
  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';

  import useStatusList from './hooks/useStatusList';

  const { t } = useI18n();

  const router = useRouter();

  const { list: statusList, defaultStatus: ticketStatus } = useStatusList();

  const { value: datePickerValue, shortcutsRange } = useDatePicker();
  const { value: searachSelectValue, searchSelectData } = useSearchSelect({
    exclude: ['status'],
  });

  const dataTableRef = useTemplateRef('list');

  // const ticketStatus = ref(defaultStatus.value);

  const ticektStatusName = computed(() => statusList.value.find((item) => item.id === ticketStatus.value)?.name);

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      todo: 'running',
      self_manage: 1,
      status: ticketStatus.value,
    });

  const { pause: pauseTicketStatus, resume: resumeTicketStatus } = watch(ticketStatus, () => {
    dataTableRef.value!.fetchData();
    router.replace({
      params: {
        status: ticketStatus.value,
      },
    });
  });

  onActivated(() => {
    // ticketStatus.value = defaultStatus.value;
    resumeTicketStatus();
  });

  onDeactivated(() => {
    pauseTicketStatus();
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
