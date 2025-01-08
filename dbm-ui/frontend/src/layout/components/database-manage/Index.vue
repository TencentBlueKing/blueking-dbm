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
        <ModuleGroup
          v-for="item in renderModuleList"
          :key="item"
          :name="item" />
        <span v-db-console="'databaseManage.addDatabaseComponents'">
          <ModuleConfig v-model="renderModuleList" />
        </span>
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
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import AppSelect from '../AppSelect.vue';
  import { useActiveKey } from '../hooks/useActiveKey';
  import { useMenuStyles } from '../hooks/useMenuStyles';

  import ModuleGroup from './components/module-group/Index.vue';
  import ModuleConfig from './components/ModuleConfig.vue';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();
  const renderModuleList = ref([]);

  const isModuleLoading = computed(() => renderModuleList.value.length < 1);

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'DatabaseTendbha', isModuleLoading);

  const styles = useMenuStyles(menuBoxRef);
</script>
