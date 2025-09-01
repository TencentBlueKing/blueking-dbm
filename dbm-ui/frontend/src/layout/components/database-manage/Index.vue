<template>
  <AppSelect
    class="mb-8"
    theme="dark" />
  <div
    ref="menuBoxRef"
    :style="styles">
    <ScrollFaker theme="dark">
      <BkMenu
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
        <BkMenuGroup
          v-db-console="'personalWorkbench'"
          :name="t('数据库部署')">
          <BkMenuItem
            key="BussinessServiceApply"
            v-db-console="'personalWorkbench.serviceApply'">
            <template #icon>
              <DbIcon type="ticket" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('部署申请') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup
          v-db-console="'databaseManage.temporaryPaasswordModify'"
          :name="t('安全')">
          <BkMenuItem key="DBPasswordTemporaryModify">
            <template #icon>
              <DbIcon type="password" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('临时密码修改') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup
          v-db-console="'databaseManage.missionManage'"
          :name="t('单据中心')">
          <BkMenuItem
            key="bizTicketManage"
            v-db-console="'databaseManage.missionManage.ticketManage'">
            <template #icon>
              <DbIcon type="ticket" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('单据') }}
            </span>
          </BkMenuItem>
          <BkMenuItem
            key="taskHistory"
            v-db-console="'databaseManage.missionManage.historyMission'">
            <template #icon>
              <DbIcon type="history" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('历史任务') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
      </BkMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { Menu } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { useBizDbDisplay } from '@hooks';

  import AppSelect from '../AppSelect.vue';
  import { useActiveKey } from '../hooks/useActiveKey';
  import { useMenuStyles } from '../hooks/useMenuStyles';

  import ModuleGroup from './components/module-group/Index.vue';

  const router = useRouter();
  const { t } = useI18n();
  const { isError: isModuleError, isLoading: isModuleLoading, tabList } = useBizDbDisplay();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();

  const renderModuleList = computed(() => tabList.value.map((tabItem) => tabItem.id));

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'BussinessServiceApply', isModuleLoading, {
    handleDefaultRouteChange() {
      // isModuleLoading 为 false，且经过内部的nextTick，代表已获取到 tabList 的值
      if (tabList.value.length === 0 || isModuleError.value) {
        router.replace({ name: 'BussinessServiceApply' });
      } else {
        router.replace({ name: `${tabList.value[0].routeIndexName}` });
      }
    },
  });

  const styles = useMenuStyles(menuBoxRef);
</script>

<style lang="less">
  .rende-db-module-move {
    transition: all 0.5s cubic-bezier(0.55, 0, 0.1, 1);
  }
</style>
