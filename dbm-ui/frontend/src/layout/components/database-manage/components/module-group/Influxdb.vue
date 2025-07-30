<template>
  <FunController
    controller-id="influxdb"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.INFLUXDB"
      :is-error="isError">
      <BkMenuItem key="InfluxDBManage">
        <template #icon>
          <DbIcon type="influxdb" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('实例管理') }}
        </span>
        <CountTag
          :cluster-type="ClusterTypes.INFLUXDB"
          role="instance" />
      </BkMenuItem>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
