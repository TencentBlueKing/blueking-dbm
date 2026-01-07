<template>
  <Teleport to="#dbContentTitleAppend">
    <div class="cluster-disable-todo-action-box">
      <BkPopover
        placement="top"
        :z-index="99999">
        <DbIcon type="attention" />
        <template #content>
          <div>{{ t('待我处理：通常是我发起禁用的单据，或者我是业务主DBA') }}</div>
          <div>{{ t('待我协助：通常是我被设定为业务协助人，或者我是业务的备DBA、二线 DBA') }}</div>
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
          <span>{{ t('待我协助') }} ({{ toAssistCount }})</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { useUrlSearch } from '@hooks';

  import { DBTypes } from '@common/const';

  interface Props {
    dbType: DBTypes;
    toAssistCount: number;
    todoCount: number;
  }

  type Emits = (e: 'change', value: number) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number>({
    required: true,
  });

  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const { t } = useI18n();

  const handleChangeAssist = (assist: number) => {
    router.replace({
      params: {
        assist,
        dbType: props.dbType,
      },
      query: {
        ...getSearchParams(),
      },
    });
    setTimeout(() => {
      modelValue.value = assist;
      emits('change', assist);
    });
  };
</script>

<style lang="less">
  .cluster-disable-todo-action-box {
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
