<template>
  <FunController
    controller-id="doris"
    module-id="bigdata">
    <BkMenuGroup name="Doris">
      <BkMenuItem key="DorisManage">
        <template #icon>
          <DbIcon type="doris" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('集群管理') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
  </FunController>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
