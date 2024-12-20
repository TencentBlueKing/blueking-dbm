<template>
  <FunController
    controller-id="riak"
    module-id="bigdata">
    <BkMenuGroup name="Riak">
      <BkMenuItem key="RiakManage">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('集群管理') }}
        </span>
        <CountTag
          :cluster-type="ClusterTypes.RIAK"
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
