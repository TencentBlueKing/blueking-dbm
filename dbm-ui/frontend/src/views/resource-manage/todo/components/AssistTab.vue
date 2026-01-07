<template>
  <Teleport to="#dbContentTitleAppend">
    <BkPopover
      placement="top"
      :z-index="99999">
      <div class="host-todo-page-title-icon">
        <DbIcon type="attention" />
      </div>
      <template #content>
        <div>{{ t('故障池主机：展示待我处理的故障主机，一般是uwork、xwork检测有异常的已下架主机') }}</div>
        <div>{{ t('待回收池主机：展示待我处理的待回收主机，一般是检测为Windows、待裁撤主机的已下架主机') }}</div>
      </template>
    </BkPopover>
  </Teleport>
  <BkTab
    v-model:active="modelValue"
    class="host-todo-assist-tab"
    type="unborder-card"
    @change="handleChangeType">
    <BkTabPanel
      v-for="tab in renderTabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id"
      :num="tab.count"
      num-display-type="bracket" />
  </BkTab>
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

  const renderTabs = computed(() => {
    return [
      {
        count: faultCount.value,
        id: HostHandleTodoType.FAULT_HOST,
        name: t('故障池主机'),
      },
      {
        count: recycleCount.value,
        id: HostHandleTodoType.RECYCLE_HOST,
        name: t('待回收池主机 '),
      },
    ];
  });

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
  .host-todo-page-title-icon {
    display: flex;
    padding-top: 2px;
    margin-right: 12px;
    margin-left: 6px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    align-items: center;
  }

  .host-todo-assist-tab {
    width: 100%;
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-header-nav {
      overflow: hidden;
    }

    .bk-tab-content {
      display: none;
    }
  }
</style>
