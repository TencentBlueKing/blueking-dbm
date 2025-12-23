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
        <PrimaryTable
          bordered
          :data="tableData"
          :max-height="250"
          row-key="disk_id">
          <TableColumn
            col-key="mounted_point"
            :title="t('挂载点')" />
          <TableColumn
            col-key="size"
            :title="t('容量（G）')" />
          <TableColumn
            col-key="disk_type"
            :title="t('磁盘类型')">
            <template #default="{ row }: { row: IRowData }">
              {{ deviceClassDisplayMap[row.disk_type as DeviceClass] }}
            </template>
          </TableColumn>
        </PrimaryTable>
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

  type IRowData = UnwrapRef<typeof tableData>[number];

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
