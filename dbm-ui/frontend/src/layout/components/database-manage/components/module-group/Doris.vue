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
        <CountTag
          :cluster-type="ClusterTypes.DORIS"
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
