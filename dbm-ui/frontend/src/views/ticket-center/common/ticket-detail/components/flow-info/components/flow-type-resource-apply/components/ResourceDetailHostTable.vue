<template>
  <PrimaryTable
    :data="data"
    row-key="ip">
    <TableColumn
      col-key="ip"
      fixed="left"
      title="IP"
      :width="200">
      <template #default="{ row: rowData }: { row: IResouce & { tag: string } }">
        {{ rowData.ip }}
        <BkTag v-if="rowData.tag">{{ rowData.tag }}</BkTag>
      </template>
    </TableColumn>
    <TableColumn
      col-key="for_biz"
      :min-width="300"
      :title="t('资源归属')">
      <template #default="{ row: rowData }: { row: IResouce }">
        <ResourceHostOwner :data="getResourceHostOwnerData(rowData)" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="city"
      :min-width="100"
      :title="t('地域')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ rowData.city || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="sub_zone"
      :min-width="100"
      :title="t('园区')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ rowData.sub_zone || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="rack_id"
      :min-width="100"
      :title="t('机架')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ rowData.rack_id || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="os_name"
      :min-width="180"
      :title="t('操作系统名称')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ rowData.os_name || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="os_type"
      :min-width="180"
      :title="t('操作系统')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ rowData.os_type || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="device_class"
      :min-width="100"
      :title="t('机型')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ rowData.device_class || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="bk_cpu"
      :min-width="100"
      :title="t('CPU_核_')" />
    <TableColumn
      col-key="bk_mem"
      :min-width="100"
      :title="t('内存G')">
      <template #default="{ row: rowData }: { row: IResouce }">
        {{ transformMToG(rowData.bk_mem) }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="bk_disk"
      :min-width="100"
      :title="t('磁盘G')" />
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import ResourceHostOwner from '@components/resource-host-owner/Index.vue';

  export interface IResouce {
    bk_cloud_id: number;
    bk_cpu: number;
    bk_disk: number;
    bk_mem: number;
    city: string;
    device_class: string;
    // 历史单据类型为 number; 最新单据类型{  bk_biz_id: number; bk_biz_name: string; }
    for_biz:
      | number
      | {
          bk_biz_id: number;
          bk_biz_name: string;
        };
    for_biz_info: {
      bk_biz_id: number;
      bk_biz_name: string;
    };
    ip: string;
    label_info: {
      id: number;
      name: string;
    }[];
    labels: string[];
    os_name: string;
    os_type: string;
    rack_id: string;
    resource_type: string;
    sub_zone: string;
  }

  interface Props {
    data: IResouce[];
  }

  defineProps<Props>();

  const { t } = useI18n();
  const biz = useGlobalBizs();

  const transformMToG = (value: number) => {
    return value ? (value / 1024).toFixed(2) : '--';
  };

  const getResourceHostOwnerData = (data: IResouce) => {
    if (data.for_biz_info) {
      return {
        for_biz: data.for_biz_info,
        labels: data.label_info,
        resource_type: data.resource_type,
      };
    }

    const baseData = {
      labels: [],
      resource_type: data.resource_type,
    };
    // 兼容历史单据数据结构
    if (typeof data.for_biz === 'number') {
      return {
        ...baseData,
        for_biz: {
          bk_biz_id: data.for_biz,
          bk_biz_name: biz.bizIdMap.get(data.for_biz)?.display_name || '--',
        },
      };
    }

    return {
      ...baseData,
      for_biz: data.for_biz,
    };
  };
</script>
