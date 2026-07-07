<template>
  <FunController module-id="k8s">
    <MenuGroup
      :db-type="DBTypes.K8S_QRRANT"
      :is-error="isError">
      <FunController
        controller-id="k8s_qdrant"
        module-id="k8s">
        <DbMenuItem
          icon="cluster"
          route-name="QdrantHaList">
          {{ t('集群管理') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.K8S_QDRANT_HA"
              role="cluster" />
          </template>
        </DbMenuItem>
      </FunController>
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
