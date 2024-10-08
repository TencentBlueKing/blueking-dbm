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
        <BkMenuGroup :name="t('资源管理')">
          <BkMenuItem
            key="BizResourcePool"
            v-db-console="'bizConfigManage.businessResourcePool'">
            <template #icon>
              <DbIcon
                svg
                type="list" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('资源池') }}
            </span>
          </BkMenuItem>
          <BkMenuItem
            key="BizResourceTag"
            v-db-console="'bizConfigManage.businessResourceTag'">
            <template #icon>
              <DbIcon
                svg
                type="tag-3" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('资源标签') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup :name="t('业务配置')">
          <BkMenuItem
            key="DbConfigure"
            v-db-console="'bizConfigManage.dbConfigure'">
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
          <BkMenuItem
            key="DBMonitorStrategy"
            v-db-console="'bizConfigManage.monitorStrategy'">
            <template #icon>
              <DbIcon type="gaojingcelve" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('监控策略') }}
            </span>
          </BkMenuItem>
          <BkMenuItem
            key="DBMonitorAlarmGroup"
            v-db-console="'bizConfigManage.alarmGroup'">
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
        <BkMenuGroup :name="t('单据配置')">
          <BkMenuItem
            key="TicketFlowSetting"
            v-db-console="'bizConfigManage.ticketFlowSetting'">
            <template #icon>
              <DbIcon type="db-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('单据免审批设置') }}
            </span>
          </BkMenuItem>
          <BkMenuItem
            key="TicketCooperationSetting"
            v-db-console="'bizConfigManage.ticketCooperationSetting'">
            <template #icon>
              <DbIcon type="lianxi" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('单据协作设置') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup :name="t('设置')">
          <BkMenuItem
            key="StaffManage"
            v-db-console="'bizConfigManage.StaffManage'">
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

  import AppSelect from './AppSelect.vue';
  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'BizResourcePool');

  const styles = useMenuStyles(menuBoxRef);
</script>
