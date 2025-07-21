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
          <ModuleGroup
            v-for="item in renderModuleList"
            :key="item"
            :name="item" />
        </BkLoading>
        <BkMenuGroup
          v-db-console="'personalWorkbench'"
          :name="t('服务申请')">
          <BkMenuItem
            key="BussinessServiceApply"
            v-db-console="'personalWorkbench.serviceApply'">
            <template #icon>
              <DbIcon type="ticket" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('服务申请') }}
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

  // const router = useRouter();
  const { t } = useI18n();
  const { isLoading: isModuleLoading, tabList } = useBizDbDisplay();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();
  const renderModuleList = ref<string[]>([]);

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'BussinessServiceApply', isModuleLoading);

  const styles = useMenuStyles(menuBoxRef);

  watch(tabList, () => {
    setTimeout(() => {
      if (tabList.value.length === 0) {
        renderModuleList.value = [];
        // router.replace({ name: 'BussinessServiceApply' });
      } else {
        renderModuleList.value = tabList.value.map((tabItem) => tabItem.id);
        // router.replace({ name: `${tabList.value[0].routeIndexName}` });
      }
    });
  });
</script>
