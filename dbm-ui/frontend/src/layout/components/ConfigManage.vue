<template>
  <AppSelect />
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
          v-if="userProfile.resourceManage"
          :fold-name="t('资源')"
          :name="t('资源管理')">
          <DbMenuItem
            v-db-console="'bizConfigManage.businessResourcePool'"
            icon="list"
            route-name="BizResourcePool"
            svg>
            {{ t('资源池') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'bizConfigManage.businessResourceTag'"
            icon="tag-3"
            route-name="BizResourceTag"
            svg>
            {{ t('资源标签') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          :fold-name="t('参数')"
          :name="t('参数配置')">
          <DbMenuItem
            v-db-console="'bizConfigManage.dbConfigure'"
            icon="db-config"
            route-name="DbConfigure">
            {{ t('数据库配置') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'bizConfigManage.backupStorageConfig'"
            icon="backup"
            route-name="BackupStorageConfig">
            {{ t('备份存储配置') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          :fold-name="t('告警')"
          :name="t('监控告警')">
          <DbMenuItem
            v-db-console="'bizConfigManage.monitorStrategy'"
            icon="gaojingcelve"
            route-name="monitorStrategy">
            {{ t('告警策略') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'bizConfigManage.alarmGroup'"
            icon="yonghuzu"
            route-name="alarmGroup">
            {{ t('告警组') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'bizConfigManage.alarmShield'"
            icon="pingbi"
            route-name="AlarmShield">
            {{ t('告警屏蔽') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          :fold-name="t('单据')"
          :name="t('单据配置')">
          <DbMenuItem
            v-db-console="'bizConfigManage.ticketFlowSetting'"
            icon="db-config"
            route-name="TicketFlowSetting">
            {{ t('单据审批设置') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'bizConfigManage.ticketCooperationSetting'"
            icon="lianxi"
            route-name="TicketCooperationSetting">
            {{ t('单据协作设置') }}
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'bizConfigManage.ticketNoticeSetting'"
            icon="note"
            route-name="TicketNoticeSetting">
            {{ t('单据通知') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup :name="t('设置')">
          <DbMenuItem
            v-db-console="'bizConfigManage.StaffManage'"
            icon="dba-config"
            route-name="StaffManage">
            {{ t('DBA 管理') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup :name="t('其他')">
          <DbMenuItem
            v-db-console="'bizConfigManage.businessClusterTag'"
            icon="tag-3"
            route-name="businessClusterTag">
            {{ t('集群标签管理') }}
          </DbMenuItem>
        </DbMenuGroup>
      </DbMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import AppSelect from './AppSelect.vue';
  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';

  const { t } = useI18n();
  const userProfile = useUserProfile();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef, userProfile.resourceManage ? 'BizResourcePool' : 'DbConfigure');

  const styles = useMenuStyles(menuBoxRef);
</script>
