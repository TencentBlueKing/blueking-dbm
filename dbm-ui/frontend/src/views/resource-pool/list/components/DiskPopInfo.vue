<template>
  <BkPopover
    :popover-delay="[0, 300]"
    theme="light"
    trigger="hover"
    :width="430">
    <span style="padding: 0 10px">
      <slot />
    </span>
    <template #content>
      <div style="padding: 8px 1px">
        <BkTable
          border="outer"
          :columns="tableColumns"
          :data="tableData"
          :max-height="250" />
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

  const tableData = computed(() => Object.keys(props.data).map(key => ({
    ...props.data[key],
    mounted_point: key,
  })));

  const tableColumns = [
    {
      label: t('挂载点'),
      field: 'mounted_point',
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
