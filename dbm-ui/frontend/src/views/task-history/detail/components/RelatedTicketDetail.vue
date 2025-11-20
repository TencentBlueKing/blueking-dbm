<template>
  <BkSideslider
    v-model:is-show="isShow"
    class="related-ticket-detail-slider"
    quick-close
    render-directive="if"
    title="关联单据"
    :width="1230">
    <div
      class="related-ticket-dialog-close"
      @click="handleClose">
      <DbIcon type="close" />
    </div>
    <TicketDetail
      v-if="ticketId"
      :ticket-id="ticketId" />
  </BkSideslider>
</template>
<script setup lang="ts">
  import TicketDetail from '@components/ticket-detail/index.vue';

  interface Props {
    ticketId?: number;
  }

  defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const handleClose = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .related-ticket-detail-slider {
    .bk-modal-header {
      display: none;
    }

    .bk-modal-body {
      background: #f0f1f5;
    }

    .related-ticket-dialog-close {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 99999;
      display: flex;
      width: 32px;
      height: 32px;
      font-size: 24px;
      color: #979ba5;
      cursor: pointer;
      background: #dcdee5;
      border-radius: 2px;
      justify-content: center;
      align-items: center;

      &:hover {
        background: #c4c6cc;
      }
    }
  }
</style>
