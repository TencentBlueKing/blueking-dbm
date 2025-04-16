<template>
  <AppSelect />
  <div
    ref="menuBoxRef"
    :style="styles">
    <ScrollFaker theme="dark">
      <BkMenu
        ref="menuRef"
        :active-key="currentActiveKey"
        :opened-keys="[parentKey]"
        @click="handleMenuChange">
        <BkMenuGroup
          v-db-console="'observableManage.AlarmEvents'"
          :name="t('告警')">
          <BkMenuItem key="AlarmEvents">
            <template #icon>
              <DbIcon type="db-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('告警事件') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup
          v-db-console="'observableManage.DBHASwitchEvents'"
          name="DBHA">
          <BkMenuItem key="DBHASwitchEvents">
            <template #icon>
              <DbIcon type="db-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('DBHA切换事件') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup
          v-db-console="'observableManage.healthReport'"
          :name="t('巡检')">
          <BkMenuItem key="inspectionManage">
            <template #icon>
              <DbIcon type="db-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('巡检报告') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
      </BkMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { Menu } from 'bkui-vue';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import AppSelect from './AppSelect.vue';
  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'AlarmEvents');
  const styles = useMenuStyles(menuBoxRef);
</script>
