<template>
  <BkTable
    :data="data"
    :row-config="{
      useKey: true,
      keyField: 'ip',
    }">
    <BkTableColumn
      field="ip"
      fixed="left"
      label="IP"
      :width="200">
      <template #default="{ data }: { data: IResouce & { tag: string } }">
        {{ data.ip }}
        <BkTag v-if="data.tag">{{ data.tag }}</BkTag>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="city"
      :label="t('地域')"
      :min-width="100">
      <template #default="{ data }: { data: IResouce }">
        {{ data.city || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="sub_zone"
      :label="t('园区')"
      :min-width="100">
      <template #default="{ data }: { data: IResouce }">
        {{ data.sub_zone || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="rack_id"
      :label="t('机架')"
      :min-width="100">
      <template #default="{ data }: { data: IResouce }">
        {{ data.rack_id || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="os_type"
      :label="t('操作系统名称')"
      :min-width="180">
      <template #default="{ data }: { data: IResouce }">
        {{ data.os_type || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="device_class"
      :label="t('机型')"
      :min-width="100">
      <template #default="{ data }: { data: IResouce }">
        {{ data.device_class || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="bk_cpu"
      :label="t('CPU_核_')"
      :min-width="100" />
    <BkTableColumn
      field="bk_mem"
      :label="t('内存M')"
      :min-width="100" />
    <BkTableColumn
      field="bk_disk"
      :label="t('磁盘G')"
      :min-width="100" />
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  export interface IResouce {
    bk_cloud_id: number;
    bk_cpu: number;
    bk_disk: number;
    bk_mem: number;
    city: string;
    device_class: string;
    ip: string;
    os_name: string;
    os_type: string;
    rack_id: string;
    sub_zone: string;
  }

  interface Props {
    data: IResouce[];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
