<template>
  <FunController
    controller-id="kafka"
    module-id="bigdata">
    <BkMenuGroup name="Kafka">
      <BkMenuItem key="KafkaManage">
        <template #icon>
          <DbIcon type="kafka" />
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
