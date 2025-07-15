<template>
  <!-- <FunController
    controller-id="es"
    module-id="bigdata"> -->
  <!-- <MenuGroup :db-type="DBTypes.ES"> -->
  <BkMenuGroup name="ES">
    <BkMenuItem key="EsManage">
      <template #icon>
        <DbIcon type="es" />
      </template>
      <span
        v-overflow-tips.right
        class="text-overflow">
        {{ t('集群管理') }}
      </span>
      <CountTag
        :cluster-type="ClusterTypes.ES"
        role="cluster" />
    </BkMenuItem>
  </BkMenuGroup>
  <!-- </MenuGroup> -->
  <!-- </FunController> -->
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import CountTag from './components/CountTag.vue';
  // import MenuGroup from './components/MenuGroup.vue';

  const { t } = useI18n();
</script>
