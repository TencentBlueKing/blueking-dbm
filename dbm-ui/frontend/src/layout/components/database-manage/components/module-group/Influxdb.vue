<template>
  <FunController
    controller-id="influxdb"
    module-id="bigdata">
    <BkMenuGroup name="InfluxDB">
      <BkMenuItem key="InfluxDBManage">
        <template #icon>
          <DbIcon type="influxdb" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('实例管理') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
