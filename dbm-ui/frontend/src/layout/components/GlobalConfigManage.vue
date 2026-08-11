<template>
  <div
    ref="menuBoxRef"
    :style="styles">
    <ScrollFaker theme="dark">
      <DbMenu
        ref="menuRef"
        :active-key="currentActiveKey"
        :opened-keys="[parentKey]"
        @click="handleMenuChange">
        <DbMenuGroup
          v-db-console="'globalConfigManage.versionFile'"
          :name="t('版本')">
          <DbMenuItem
            icon="version"
            route-name="PlatformVersionFiles">
            {{ t('版本管理') }}
          </DbMenuItem>
          <DbMenuItem
            v-show="false"
            icon="version"
            route-name="PlatformVersionFilesV1">
            {{ t('版本管理') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          v-db-console="'globalConfigManage.dbConfig'"
          :fold-name="t('参数')"
          :name="t('参数配置')">
          <DbMenuItem
            icon="db-config"
            route-name="PlatformDbConfigure">
            {{ t('数据库配置定义') }}
          </DbMenuItem>
        </DbMenuGroup>
        <FunController module-id="monitor">
          <DbMenuGroup
            v-db-console="'globalConfigManage.monitorStrategy'"
            :fold-name="t('告警')"
            :name="t('监控告警')">
            <FunController
              controller-id="monitor_policy"
              module-id="monitor">
              <DbMenuItem
                icon="gaojingcelve"
                route-name="PlatGlobalStrategy">
                {{ t('全局告警策略') }}
              </DbMenuItem>
            </FunController>
          </DbMenuGroup>
        </FunController>
        <FunController module-id="monitor">
          <DbMenuGroup
            v-db-console="'globalConfigManage.rotationManage'"
            :name="t('轮值')">
            <FunController
              controller-id="duty_rule"
              module-id="monitor">
              <DbMenuItem
                icon="db-config"
                route-name="dutyRuleManange">
                {{ t('轮值策略') }}
              </DbMenuItem>
            </FunController>
            <FunController
              controller-id="monitor_policy"
              module-id="monitor">
              <DbMenuItem
                icon="note"
                route-name="PlatformNotificationSetting">
                {{ t('轮值通知') }}
              </DbMenuItem>
            </FunController>
          </DbMenuGroup>
        </FunController>
        <DbMenuGroup
          v-db-console="'globalConfigManage.passwordSafe'"
          :fold-name="t('密码')"
          :name="t('密码安全')">
          <DbMenuItem
            icon="pingbi"
            route-name="PlatformPasswordRandomization">
            {{ t('密码随机化管理') }}
          </DbMenuItem>
          <DbMenuItem
            icon="password"
            route-name="PlatformPasswordPolicy">
            {{ t('密码安全规则') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup :name="t('设置')">
          <DbMenuItem
            v-db-console="'globalConfigManage.staffManage'"
            icon="dba-config"
            route-name="PlatformStaffManage">
            {{ t('业务与 DBA 管理') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'globalConfigManage.ticketFlowSetting'"
            icon="dba-config"
            route-name="PlatformTicketFlowSetting">
            {{ t('单据流程设置') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'globalConfigManage.todoRemind'"
            icon="note"
            route-name="TodoRemind">
            {{ t('每日待办提醒') }}
          </DbMenuItem>
          <DbSubmenu
            id="platform-mysql"
            v-db-console="'globalConfigManage.whitelistManage'"
            icon="mysql"
            title="MySQL">
            <DbMenuItem route-name="PlatformWhitelist">
              {{ t('授权白名单') }}
            </DbMenuItem>
          </DbSubmenu>
        </DbMenuGroup>
      </DbMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';
  import DbSubmenu from './menu/Submenu.vue';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef, 'PlatformVersionFiles');

  const styles = useMenuStyles(menuBoxRef);
</script>
