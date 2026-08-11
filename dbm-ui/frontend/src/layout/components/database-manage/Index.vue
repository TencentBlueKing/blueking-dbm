<template>
  <AppSelect
    class="mb-8"
    theme="dark" />
  <div
    ref="menuBoxRef"
    :style="styles">
    <ScrollFaker theme="dark">
      <DbMenu
        ref="menuRef"
        :active-key="currentActiveKey"
        :opened-keys="[parentKey]"
        @click="handleMenuChange">
        <BkLoading
          :loading="isModuleLoading"
          :style="{ minHeight: isModuleLoading ? '30px' : 0 }">
          <template v-if="!isModuleLoading">
            <TransitionGroup name="rende-db-module">
              <ModuleGroup
                v-for="item in renderModuleList"
                :key="item"
                :is-error="isModuleError"
                :name="item" />
            </TransitionGroup>
          </template>
        </BkLoading>
        <DbMenuGroup
          v-db-console="'personalWorkbench'"
          :fold-name="t('部署')"
          :name="t('数据库部署')">
          <DbMenuItem
            v-db-console="'personalWorkbench.serviceApply'"
            icon="ticket"
            route-name="BussinessServiceApply">
            {{ t('部署申请') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          v-db-console="'databaseManage.temporaryPaasswordModify'"
          :name="t('安全')">
          <DbMenuItem
            icon="password"
            route-name="DBPasswordTemporaryModify">
            {{ t('临时密码修改') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          v-db-console="'databaseManage.missionManage'"
          :fold-name="t('单据')"
          :name="t('单据中心')">
          <DbMenuItem
            v-db-console="'databaseManage.missionManage.ticketManage'"
            icon="ticket"
            route-name="bizTicketManage">
            {{ t('单据') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'databaseManage.missionManage.historyMission'"
            icon="history"
            route-name="taskHistory">
            {{ t('历史任务') }}
          </DbMenuItem>
        </DbMenuGroup>
      </DbMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts" async>
  import { useI18n } from 'vue-i18n';

  import { useBizDbDisplay } from '@hooks';

  import AppSelect from '../AppSelect.vue';
  import { useActiveKey } from '../hooks/useActiveKey';
  import { useMenuStyles } from '../hooks/useMenuStyles';
  import DbMenuGroup from '../menu/Group.vue';
  import DbMenu from '../menu/Index.vue';
  import DbMenuItem from '../menu/Item.vue';

  import ModuleGroup from './components/module-group/Index.vue';

  const { t } = useI18n();
  const {
    fetchClusterInstanceCount,
    isError: isModuleError,
    isLoading: isModuleLoading,
    tabList,
  } = useBizDbDisplay({
    manual: true,
  });

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const renderModuleList = computed(() => tabList.value.map((tabItem) => tabItem.id));

  await fetchClusterInstanceCount();

  const defaultRouterName =
    tabList.value.length === 0 || isModuleError.value ? 'BussinessServiceApply' : tabList.value[0]!.routeIndexName;

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef, defaultRouterName);

  const styles = useMenuStyles(menuBoxRef);
</script>
<style lang="less">
  .rende-db-module-move {
    transition: all 0.5s cubic-bezier(0.55, 0, 0.1, 1);
  }
</style>
