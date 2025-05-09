<template>
  <div>
    <div
      ref="handleRef"
      class="cluster-detail-related-ticket-box"
      :class="{
        [`is-size-${size}`]: true,
      }">
      {{ data.length }}
    </div>
    <div
      ref="popRef"
      class="cluster-detail-related-ticket-popover">
      <ScrollFaker v-if="isActive">
        <div
          v-for="item in data"
          :key="item.ticket_id"
          class="cluster-related-ticket-item">
          <TicketStatusTag
            class="mr-4"
            :data="{
              status: item.status as TicketModel['status'],
              statusText: TicketModel.statusTextMap[item.status as TicketModel['status']],
            }"
            small />
          【{{ item.title }}】
          {{ t('单据ID') }}
          <span>:</span>
          <RouterLink
            class="ml-4"
            target="_blank"
            :to="{
              name: 'bizTicketManage',
              params: {
                ticketId: item.ticket_id,
              },
            }">
            #{{ item.ticket_id }}
          </RouterLink>
        </div>
      </ScrollFaker>
    </div>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import type { ClusterListOperation } from '@services/types';

  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  interface Props {
    data: ClusterListOperation[];
    size?: 'default' | 'big';
  }

  type Emits = (e: 'toogle-show', value: boolean) => void;

  withDefaults(defineProps<Props>(), {
    size: 'default',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let tippyIns: Instance;
  const isActive = ref(false);
  const handleRef = ref();
  const popRef = ref();

  onMounted(() => {
    tippyIns = tippy(handleRef.value as SingleTarget, {
      allowHTML: true,
      appendTo: () => document.body,
      content: popRef.value,
      hideOnClick: true,
      interactive: true,
      maxWidth: 'none',
      onHide() {
        isActive.value = false;
        emits('toogle-show', false);
      },
      onShow() {
        isActive.value = true;
        emits('toogle-show', true);
      },
      placement: 'bottom',
      theme: 'light',
      zIndex: 999,
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });
</script>
<style lang="less">
  .cluster-detail-related-ticket-box {
    display: flex;
    height: 16px;
    padding: 0 4px;
    line-height: 1;
    color: #3a84ff;
    white-space: nowrap;
    background: #e1ecff;
    background-color: #e1ecff;
    border: 1px solid #a3c5fd;
    border-radius: 2px;
    align-items: center;

    &.is-size-big {
      height: 22px;
      padding: 0 8px;
      font-size: 12px;
    }
  }

  .cluster-detail-related-ticket-popover {
    max-height: 350px;

    .scroll-faker > .scroll-faker-content {
      max-height: inherit;
      padding: 3px;
    }
  }

  .cluster-related-ticket-item {
    display: flex;
    width: 100%;
    padding: 4px 0;
    align-items: center;
    font-size: 12px;
    color: #63656e;
  }
</style>
