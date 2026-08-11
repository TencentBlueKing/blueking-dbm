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
          v-db-console="'observableManage.AlarmEvents'"
          :fold-name="t('告警')"
          :name="t('监控告警')">
          <DbMenuItem
            icon="db-config"
            route-name="bussinessDashboard">
            {{ t('业务监控大盘') }}
          </DbMenuItem>
          <DbMenuItem
            icon="db-config"
            route-name="AlarmEvents">
            {{ t('告警事件') }}
          </DbMenuItem>
          <DbMenuItem
            icon="file"
            route-name="RiskMemo">
            {{ t('风险备忘录') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          v-db-console="'observableManage.DBHASwitchEvents'"
          name="DBHA">
          <DbMenuItem
            icon="db-config"
            route-name="DBHASwitchEvents">
            {{ t('DBHA切换事件') }}
          </DbMenuItem>
        </DbMenuGroup>
        <DbMenuGroup
          v-db-console="'observableManage.healthReport'"
          :name="t('巡检')">
          <DbMenuItem
            icon="db-config"
            route-name="inspectionManage">
            {{ t('巡检报告') }}
          </DbMenuItem>
        </DbMenuGroup>
      </DbMenu>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import AppSelect from './AppSelect.vue';
  import { useActiveKey } from './hooks/useActiveKey';
  import { useMenuStyles } from './hooks/useMenuStyles';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';

  const { t } = useI18n();

  const menuBoxRef = ref<HTMLElement>();
  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const {
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef, 'bussinessDashboard');
  const styles = useMenuStyles(menuBoxRef);
</script>
