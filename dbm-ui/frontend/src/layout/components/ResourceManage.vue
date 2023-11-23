<template>
  <BkMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <BkMenuGroup :name="t('资源管理')">
      <BkMenuItem key="resourceSpec">
        <template #icon>
          <DbIcon type="spec" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('资源规格管理') }}
        </span>
      </BkMenuItem>
      <BkMenuItem key="resourcePoolList">
        <template #icon>
          <DbIcon type="list" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('DB 资源池管理') }}
        </span>
      </BkMenuItem>
      <BkMenuItem key="resourcePoolDirtyMachines">
        <template #icon>
          <DbIcon type="dirty-host" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('污点主机处理') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
  </BkMenu>
</template>
<script setup lang="ts">
  import { Menu } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { useActiveKey } from './hooks/useActiveKey';

  const { t } = useI18n();

  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'resourceSpec');

</script>

