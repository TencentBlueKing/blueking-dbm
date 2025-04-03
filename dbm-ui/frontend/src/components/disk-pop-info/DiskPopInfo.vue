<template>
  <BkPopover
    :popover-delay="50"
    theme="light"
    :trigger="trigger"
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
    data: DbResourceModel['storage_device'];
    trigger?: 'hover' | 'click' | 'manual';
  }

  const props = withDefaults(defineProps<Props>(), {
    trigger: 'hover',
  });

  const { t } = useI18n();

  const tableData = computed(() =>
    Object.keys(props.data).map((key) => ({
      ...props.data[key],
      mounted_point: key,
    })),
  );

  const tableColumns = [
    {
      field: 'mounted_point',
      label: t('挂载点'),
    },
    {
      field: 'size',
      label: t('容量（G）'),
    },
    {
      field: 'disk_type',
      label: t('磁盘类型'),
    },
  ];
</script>
