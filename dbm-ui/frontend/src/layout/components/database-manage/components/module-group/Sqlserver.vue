<template>
  <FunController module-id="sqlserver">
    <BkMenuGroup name="Sqlserver">
      <BkSubmenu
        key="SqlserverHaClusterManage"
        :title="t('主从')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="SqlserverHaClusterList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群视图') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
      <BkMenuItem key="Sqlserversingle">
        <template #icon>
          <DbIcon type="node" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('单节点') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
