<template>
  <FunController
    controller-id="doris"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.DORIS"
      :is-error="isError">
      <BkMenuItem key="DorisManage">
        <template #icon>
          <DbIcon type="doris" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('集群管理') }}
        </span>
        <CountTag
          :cluster-type="ClusterTypes.DORIS"
          role="cluster" />
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
