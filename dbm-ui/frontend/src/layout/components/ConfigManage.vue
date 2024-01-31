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
        <BkMenuGroup :name="t('业务配置')">
          <BkMenuItem key="DbConfigure">
            <template #icon>
              <DbIcon type="db-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('数据库配置') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup :name="t('监控告警')">
          <BkMenuItem key="DBMonitorStrategy">
            <template #icon>
              <DbIcon type="gaojingcelve" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('监控策略') }}
            </span>
          </BkMenuItem>
          <BkMenuItem key="DBMonitorAlarmGroup">
            <template #icon>
              <DbIcon type="yonghuzu" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('告警组') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup :name="t('设置')">
          <BkMenuItem key="StaffManage">
            <template #icon>
              <DbIcon type="db-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('DBA人员管理') }}
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

  import AppSelect from '@components/app-select/Index.vue';

  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'DbConfigure');

  const styles = useMenuStyles(menuBoxRef);

</script>

