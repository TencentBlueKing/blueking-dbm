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
          :data="tableData"
          :max-height="250">
          <BkTableColumn
            field="mounted_point"
            :label="t('挂载点')" />
          <BkTableColumn
            field="size"
            :label="t('容量（G）')" />
          <BkTableColumn
            field="disk_type"
            :label="t('磁盘类型')">
            <template #default="{ data }: { data: UnwrapRef<typeof tableData>[number] }">
              {{ deviceClassDisplayMap[data.disk_type as DeviceClass] }}
            </template>
          </BkTableColumn>
        </BkTable>
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { computed, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

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
</script>
