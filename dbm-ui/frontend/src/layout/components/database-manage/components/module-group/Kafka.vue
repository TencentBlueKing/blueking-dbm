<template>
  <FunController
    controller-id="kafka"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.KAFKA"
      :is-error="isError">
      <DbMenuItem
        icon="kafka"
        route-name="KafkaManage">
        {{ t('集群管理') }}
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.KAFKA"
            role="cluster" />
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
