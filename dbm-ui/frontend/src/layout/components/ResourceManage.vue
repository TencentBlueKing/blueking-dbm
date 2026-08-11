<template>
  <DbMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <DbMenuGroup
      :fold-name="t('资源')"
      :name="t('资源管理')">
      <DbMenuItem
        v-db-console="'resourceManage.resourcePool'"
        icon="list"
        route-name="resourcePool">
        {{ t('资源池') }}
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'resourceManage.faultPool'"
        icon="guzhangji"
        route-name="faultPool">
        {{ t('故障池') }}
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'resourceManage.toRecyclePool'"
        icon="daihuishou"
        route-name="toRecyclePool">
        {{ t('待回收池') }}
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'resourceManage.allHost'"
        icon="list"
        route-name="allHost">
        {{ t('所有主机') }}
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'resourceManage.resourceSpec'"
        icon="spec"
        route-name="resourceSpec">
        {{ t('资源规格管理') }}
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'resourceManage.resourceTagsManagement'"
        icon="tag-3"
        route-name="resourceTagsManagement">
        {{ t('资源标签管理') }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup :name="t('其他')">
      <DbMenuItem
        v-db-console="'resourceManage.resourceOperationRecord'"
        icon="list"
        route-name="resourcePoolOperationRecord">
        {{ t('资源操作记录') }}
      </DbMenuItem>
    </DbMenuGroup>
  </DbMenu>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useActiveKey } from './hooks/useActiveKey';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';

  const { t } = useI18n();

  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const { key: currentActiveKey, parentKey, routeLocation: handleMenuChange } = useActiveKey(menuRef, 'resourcePool');
</script>
