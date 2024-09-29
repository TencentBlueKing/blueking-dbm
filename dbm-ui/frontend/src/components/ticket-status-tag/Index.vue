<template>
  <div
    class="ticket-status-tag"
    :class="{ 'is-small': small }">
    {{ data.statusText }}
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    data: TicketModel;
    small?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    small: false,
  });

  const backgroundcolor = computed(() => {
    const colorMap = {
      [TicketModel.STATUS_APPROVE]: '#DAE9FD',
      [TicketModel.STATUS_FAILED]: '#EA3636',
      [TicketModel.STATUS_RESOURCE_REPLENISH]: '#DFF5FD',
      [TicketModel.STATUS_RUNNING]: '#E1ECFF',
      [TicketModel.STATUS_SUCCEEDED]: '#DAF6E5',
      [TicketModel.STATUS_TERMINATED]: '#FFEBEB',
      [TicketModel.STATUS_TIMER]: '#C8E8E6',
      [TicketModel.STATUS_TODO]: '#F0F1F5',
      [TicketModel.STATUS_INNER_TODO]: '#FDEED8',
    };

    return colorMap[props.data.status] || '#f0f1f5';
  });

  const fontdcolor = computed(() => {
    const colorMap = {
      [TicketModel.STATUS_APPROVE]: '#267BCF',
      [TicketModel.STATUS_FAILED]: '#FFFFFF',
      [TicketModel.STATUS_RESOURCE_REPLENISH]: '#2F96A7',
      [TicketModel.STATUS_RUNNING]: '#1768EF',
      [TicketModel.STATUS_SUCCEEDED]: '#299E56',
      [TicketModel.STATUS_TERMINATED]: '#E71818',
      [TicketModel.STATUS_TIMER]: '#3F726F',
      [TicketModel.STATUS_TODO]: '#4D4F56',
      [TicketModel.STATUS_INNER_TODO]: '#E38B02',
    };

    return colorMap[props.data.status] || '#63656e';
  });
</script>
<style lang="postcss">
  .ticket-status-tag {
    display: inline-flex;
    height: 22px;
    padding: 0 8px;
    font-size: 12px;
    font-weight: normal;
    color: v-bind(fontdcolor);
    background: v-bind(backgroundcolor);
    align-items: center;
    border-radius: 2px;

    &.is-small {
      height: 16px;
      padding: 0 4px;
      font-size: 10px;
      font-weight: bold;
    }
  }
</style>
