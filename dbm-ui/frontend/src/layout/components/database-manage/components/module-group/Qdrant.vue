<template>
  <FunController module-id="k8s">
    <MenuGroup
      :db-type="DBTypes.K8S_QRRANT"
      :is-error="isError">
      <FunController
        controller-id="k8s_qdrant"
        module-id="k8s">
        <BkMenuItem key="QdrantHaList">
          <template #icon>
            <DbIcon type="cluster" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群管理') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.K8S_QDRANT_HA"
            role="cluster" />
        </BkMenuItem>
      </FunController>
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
