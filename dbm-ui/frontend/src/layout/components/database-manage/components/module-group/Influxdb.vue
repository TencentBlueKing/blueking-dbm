<template>
  <FunController
    controller-id="influxdb"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.INFLUXDB"
      :is-error="isError">
      <DbMenuItem
        icon="influxdb"
        route-name="InfluxDBManage">
        {{ t('实例管理') }}
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.INFLUXDB"
            role="instance" />
        </template>
      </DbMenuItem>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import DbMenuItem from '../../../menu/Item.vue';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
