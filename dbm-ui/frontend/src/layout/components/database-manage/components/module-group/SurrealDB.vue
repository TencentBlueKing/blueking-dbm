<template>
  <FunController module-id="k8s">
    <MenuGroup
      :db-type="DBTypes.K8S_SURREALDB"
      :is-error="isError">
      <FunController
        controller-id="k8s_surrealdb"
        module-id="k8s">
        <BkMenuItem key="SurrealdbHaList">
          <template #icon>
            <DbIcon type="cluster" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群管理') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.K8S_SURREALDB_HA"
            role="cluster" />
        </BkMenuItem>
      </FunController>
      <FunController
        controller-id="k8s_surrealdb"
        module-id="k8s">
        <BkMenuItem key="SurrealdbSingleList">
          <template #icon>
            <DbIcon type="node" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('单节点') }}
            <CountTag
              :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
              role="cluster" />
          </span>
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
