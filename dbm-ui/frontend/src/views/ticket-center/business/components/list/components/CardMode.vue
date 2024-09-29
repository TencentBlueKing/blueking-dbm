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
    <div style="height: calc(100% - 112px)">
      <CardModeList :data-source="dataSource" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getTickets } from '@services/source/ticket';

  import CardModeList from '@views/ticket-center/common/CardModeList.vue';
  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';

  const { t } = useI18n();

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });

  const { value: datePickerValue, shortcutsRange } = useDatePicker();
  const { value: searachSelectValue, searchSelectData } = useSearchSelect({
    exclude: ['bk_biz_id'],
  });
</script>
<style lang="less">
  .ticket-list-card-mode {
    position: relative;
    z-index: 100;
    height: calc(100vh - var(--notice-height) - 104px);
    background: #fff;

    .action-box {
      padding: 16px 24px;
    }
  }
</style>
