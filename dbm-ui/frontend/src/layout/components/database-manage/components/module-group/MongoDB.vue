<template>
  <FunController module-id="mongodb">
    <BkMenuGroup name="mongodb">
      <BkSubmenu
        :title="t('集群管理')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="mongodbInstance">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
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
