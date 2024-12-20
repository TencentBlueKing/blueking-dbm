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
        <CountTag
          :cluster-type="ClusterTypes.HDFS"
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
