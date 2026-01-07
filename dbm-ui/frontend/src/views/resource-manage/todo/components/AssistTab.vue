<template>
  <Teleport to="#dbContentTitleAppend">
    <div class="host-todo-action-box">
      <div
        class="split-line"
        style="margin: 0 14px" />
      <div class="action-box">
        <div
          class="action-item"
          :class="{ 'is-active': modelValue === HostHandleTodoType.FAULT_HOST }"
          @click="handleChangeType(HostHandleTodoType.FAULT_HOST)">
          <DbIcon
            class="mr-4"
            type="host" />
          <span>{{ t('故障池主机') }} ({{ faultCount }})</span>
        </div>
        <div class="split-line" />
        <div
          class="action-item"
          :class="{ 'is-active': modelValue === HostHandleTodoType.RECYCLE_HOST }"
          @click="handleChangeType(HostHandleTodoType.RECYCLE_HOST)">
          <DbIcon
            class="mr-4"
            type="host" />
          <span>{{ t('待回收池主机') }} ({{ recycleCount }})</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { useHostTodoCount, useUrlSearch } from '@hooks';

  import { HostHandleTodoType } from '@common/const';

  type Emits = (e: 'change', value: HostHandleTodoType) => void;

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<HostHandleTodoType>({
    required: true,
  });

  const router = useRouter();
  const { getSearchParams } = useUrlSearch();
  const { faultCount, recycleCount } = useHostTodoCount();

  const { t } = useI18n();

  const handleChangeType = (type: HostHandleTodoType) => {
    router.replace({
      params: {
        type,
      },
      query: {
        ...getSearchParams(),
      },
    });
    setTimeout(() => {
      modelValue.value = type;
      emits('change', type);
    });
  };
</script>

<style lang="less">
  .host-todo-action-box {
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

      &:hover {
        color: #3a84ff;
      }

      &.is-active {
        color: #3a84ff;
        cursor: default;
        background-color: #f0f5ff;
      }
    }
  }
</style>
