<template>
  <BkPopover
    theme="light"
    trigger="hover"
    :width="430">
    <span>
      <slot />
    </span>
    <template #content>
      <div style="padding: 8px 1px">
        <BkTable
          border="outer"
          :columns="tableColumns"
          :data="tableData" />
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  interface Props {
    data: DbResourceModel['storage_device']
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => Object.values(props.data));

  const tableColumns = [
    {
      label: t('挂载点'),
      field: 'file_type',
    },
    {
      label: t('容量（G）'),
      field: 'size',
    },
    {
      label: t('磁盘类型'),
      field: 'disk_type',
    },
  ];
</script>
