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
        <CountTag
          :cluster-type="ClusterTypes.KAFKA"
          role="cluster" />
      </BkMenuItem>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import CountTag from './components/CountTag.vue';

  const { t } = useI18n();
</script>
