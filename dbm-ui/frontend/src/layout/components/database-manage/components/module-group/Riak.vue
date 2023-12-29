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
      </BkMenuItem>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>

