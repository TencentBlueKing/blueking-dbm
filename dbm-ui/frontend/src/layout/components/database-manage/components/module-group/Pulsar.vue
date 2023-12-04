<template>
  <FunController
    controller-id="pulsar"
    module-id="bigdata">
    <BkMenuGroup name="Pulsar">
      <BkMenuItem key="PulsarManage">
        <template #icon>
          <DbIcon type="pulsar" />
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
