<template>
  <FunController
    controller-id="riak"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.RIAK"
      :is-error="isError">
      <DbMenuItem
        icon="cluster"
        route-name="RiakManage">
        {{ t('集群管理') }}
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.RIAK"
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
