<template>
  <FunController module-id="sqlserver">
    <BkMenuGroup name="SqlServer">
      <BkMenuItem key="SqlServerSingle">
        <template #icon>
          <DbIcon type="node" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('单节点') }}
        </span>
      </BkMenuItem>
      <BkSubmenu
        key="SqlServerHaClusterManage"
        :title="t('主从')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="SqlServerHaClusterList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群视图') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
