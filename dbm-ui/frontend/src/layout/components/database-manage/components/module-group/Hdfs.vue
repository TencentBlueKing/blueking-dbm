<template>
  <FunController
    controller-id="hdfs"
    module-id="bigdata">
    <BkMenuGroup name="HDFS">
      <BkMenuItem key="HdfsManage">
        <template #icon>
          <DbIcon type="hdfs" />
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
