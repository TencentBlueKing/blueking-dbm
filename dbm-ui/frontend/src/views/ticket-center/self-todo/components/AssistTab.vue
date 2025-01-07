<template>
  <Teleport to="#dbContentTitleAppend">
    <div class="todo-ticket-action-box">
      <BkPopover placement="top">
        <DbIcon type="attention" />
        <template #content>
          <div>{{ t('待我处理：通常是我提交的单据，或者我是业务主DB') }}</div>
          <div>{{ t('待我协助：通常是我被设定为单据协助人，或者我是业务的备DBA、二线 DBA') }}</div>
        </template>
      </BkPopover>
      <div
        class="split-line"
        style="margin: 0 14px" />
      <div class="action-box">
        <div
          class="action-item"
          :class="{ 'is-active': !Boolean(modelValue) }"
          @click="handleChangeAssist(0)">
          <DbIcon
            class="mr-4"
            type="wodedaiban" />
          <span>{{ t('待我处理') }} ({{ todoCount }})</span>
        </div>
        <div class="split-line" />
        <div
          class="action-item"
          :class="{ 'is-active': Boolean(modelValue) }"
          @click="handleChangeAssist(1)">
          <DbIcon
            class="mr-4"
            type="yonghu-2" />
          <span>{{ t('待我协助') }} ({{ todoHelperCount }})</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { useTicketCount, useUrlSearch } from '@hooks';

  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const { t } = useI18n();

  const { data: ticketCount } = useTicketCount();

  const modelValue = defineModel<number>();

  const todoCount = computed(() => {
    if (!ticketCount.value) {
      return 0;
    }

    return (
      ticketCount.value.pending.APPROVE +
      ticketCount.value.pending.FAILED +
      ticketCount.value.pending.RESOURCE_REPLENISH +
      ticketCount.value.pending.INNER_TODO +
      ticketCount.value.pending.TODO
    );
  });

  const todoHelperCount = computed(() => {
    if (!ticketCount.value) {
      return 0;
    }

    return (
      ticketCount.value.to_help.APPROVE +
      ticketCount.value.to_help.FAILED +
      ticketCount.value.to_help.RESOURCE_REPLENISH +
      ticketCount.value.to_help.INNER_TODO +
      ticketCount.value.to_help.TODO
    );
  });

  const handleChangeAssist = (assist: number) => {
    router.replace({
      params: {
        assist,
        status: '',
        ticketId: '',
      },
      query: {
        ...getSearchParams(),
      },
    });
    setTimeout(() => {
      modelValue.value = assist;
    });
  };
</script>
<style lang="less">
  .todo-ticket-action-box {
    display: flex;
    align-items: center;
    margin-left: 8px;
    color: #979ba5;

    .split-line {
      width: 1px;
      height: 14px;
      background: #c4c6cc;
    }

    .action-box {
      display: flex;
      overflow: hidden;
      background-color: #f0f1f5;
      border-radius: 2px;
      align-items: center;
    }

    .action-item {
      display: flex;
      height: 32px;
      padding: 0 8px;
      font-size: 14px;
      color: #4d4f56;
      cursor: pointer;
      align-items: center;
      transition: all 0.15s;

      &.is-active {
        color: #3a84ff;
        cursor: default;
        background-color: #f0f5ff;
      }
    }
  }
</style>
