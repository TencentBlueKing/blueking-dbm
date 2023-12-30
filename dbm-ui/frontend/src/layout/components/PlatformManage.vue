<template>
  <div
    ref="menuBoxRef"
    :style="styles">
    <ScrollFaker theme="dark">
      <BkMenu
        ref="menuRef"
        :active-key="currentActiveKey"
        :opened-keys="[parentKey]"
        @click="handleMenuChange">
        <BkMenuGroup :name="t('文件管理')">
          <BkMenuItem key="PlatformVersionFiles">
            <template #icon>
              <DbIcon type="version" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('版本文件') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup :name="t('配置管理')">
          <BkMenuItem key="PlatformDbConfigure">
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
        <FunController module-id="monitor">
          <BkMenuGroup :name="t('监控告警')">
            <FunController
              controller-id="monitor_policy"
              module-id="monitor">
              <BkMenuItem key="PlatGlobalStrategy">
                <template #icon>
                  <DbIcon type="gaojingcelve" />
                </template>
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ t('全局策略') }}
                </span>
              </BkMenuItem>
            </FunController>
            <FunController
              controller-id="notice_group"
              module-id="monitor">
              <BkMenuItem key="PlatMonitorAlarmGroup">
                <template #icon>
                  <DbIcon type="yonghuzu" />
                </template>
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ t('告警组') }}
                </span>
              </BkMenuItem>
            </FunController>
          </BkMenuGroup>
        </FunController>
        <FunController module-id="monitor">
          <BkMenuGroup :name="t('轮值')">
            <FunController
              controller-id="duty_rule"
              module-id="monitor">
              <BkMenuItem key="PlatRotateSet">
                <template #icon>
                  <DbIcon type="db-config" />
                </template>
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ t('轮值策略') }}
                </span>
              </BkMenuItem>
            </FunController>
            <FunController
              controller-id="monitor_policy"
              module-id="monitor">
              <BkMenuItem key="PlatformNotificationSetting">
                <template #icon>
                  <DbIcon type="note" />
                </template>
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ t('通知设置') }}
                </span>
              </BkMenuItem>
            </FunController>
          </BkMenuGroup>
        </FunController>
        <BkMenuGroup :name="t('密码安全')">
          <BkMenuItem key="PlatformPasswordRandomization">
            <template #icon>
              <DbIcon type="pingbi" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('密码随机化管理') }}
            </span>
          </BkMenuItem>
          <BkMenuItem key="PlatformPasswordPolicy">
            <template #icon>
              <DbIcon type="password" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('密码安全规则') }}
            </span>
          </BkMenuItem>
        </BkMenuGroup>
        <BkMenuGroup :name="t('设置')">
          <BkMenuItem key="PlatformStaff">
            <template #icon>
              <DbIcon type="dba-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('DBA人员管理') }}
            </span>
          </BkMenuItem>
          <BkMenuItem key="PlatformTicketFlowSetting">
            <template #icon>
              <DbIcon type="dba-config" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('单据流程设置') }}
            </span>
          </BkMenuItem>
          <BkSubmenu
            key="platform-mysql"
            title="MySQL">
            <template #icon>
              <DbIcon type="mysql" />
            </template>
            <BkMenuItem key="PlatformWhitelist">
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ t('授权白名单') }}
              </span>
            </BkMenuItem>
          </BkSubmenu>
        </BkMenuGroup>
      </BkMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { Menu } from 'bkui-vue';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'PlatformVersionFiles');

  const styles = useMenuStyles(menuBoxRef);

</script>
