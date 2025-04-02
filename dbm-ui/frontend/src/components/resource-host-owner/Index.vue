<template>
  <div class="resource-host-owner">
    <BkTag :theme="isForBiz ? 'success' : undefined">
      {{ t('所属业务') }}: {{ isForBiz ? props.data.for_biz.bk_biz_name : t('公共资源池') }}
    </BkTag>
    <BkTag :theme="isForDb ? 'success' : undefined">
      {{ t('所属DB') }}:
      {{
        isForDb && DBTypeInfos[data.resource_type as DBTypes]
          ? DBTypeInfos[data.resource_type as DBTypes].name
          : t('通用')
      }}
    </BkTag>
    <BkTag
      v-for="labelItem in data.labels"
      :key="labelItem.id">
      {{ labelItem.name || '--' }}
    </BkTag>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { DBTypeInfos, DBTypes } from '@common/const';

  interface Props {
    data: DbResourceModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isForBiz = computed(() => props.data.for_biz.bk_biz_id);
  const isForDb = computed(() => props.data.resource_type && props.data.resource_type !== 'PUBLIC');
</script>
<style lang="less">
  .resource-host-owner {
    display: inline-flex;
  }
</style>
