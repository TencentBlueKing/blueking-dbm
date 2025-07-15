<template>
  <!-- <FunController
    controller-id="kafka"
    module-id="bigdata"> -->
  <!-- <MenuGroup :db-type="DBTypes.KAFKA"> -->
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
  <!-- </MenuGroup> -->
  <!-- </FunController> -->
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import CountTag from './components/CountTag.vue';
  // import MenuGroup from './components/MenuGroup.vue';

  const { t } = useI18n();
</script>
