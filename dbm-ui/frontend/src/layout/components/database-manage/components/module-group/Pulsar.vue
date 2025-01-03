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
        <CountTag
          :cluster-type="ClusterTypes.PULSAR"
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
