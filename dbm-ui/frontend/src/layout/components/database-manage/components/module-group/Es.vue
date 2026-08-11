<template>
  <FunController
    controller-id="es"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.ES"
      :is-error="isError">
      <DbMenuItem
        icon="es"
        route-name="EsManage">
        {{ t('集群管理') }}
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.ES"
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
