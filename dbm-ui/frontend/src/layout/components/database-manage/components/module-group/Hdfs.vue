<template>
  <FunController
    controller-id="hdfs"
    module-id="bigdata">
    <MenuGroup
      :db-type="DBTypes.HDFS"
      :is-error="isError">
      <DbMenuItem
        icon="hdfs"
        route-name="HdfsManage">
        {{ t('集群管理') }}
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.HDFS"
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
