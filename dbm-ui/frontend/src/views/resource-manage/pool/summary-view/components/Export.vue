<template>
  <div
    class="export-excel"
    @click="handleClick">
    <DbIcon type="bk-dbm-icon db-icon-daochu-2" />
    <span class="ml-2">{{ t('导出列表内容') }}</span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import * as XLSX from 'xlsx';

  import type SummaryModel from '@services/model/db-resource/summary';

  interface Props {
    data: SummaryModel[];
    dimension: 'spec' | 'device_class';
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const configMap = {
    spec: {
      header: [t('专用业务'), t('地域'), t('规格类型'), t('规格'), t('园区分布（台）'), t('总数（台）')],
      colWidth: [15, 15, 30, 30, 50, 10],
      fileName: t('专用业务 + 地域 + 规格'),
    },
    device_class: {
      header: [t('专用业务'), t('地域'), t('机型（硬盘）'), t('CPU 内存'), t('园区分布（台）'), t('总数（台）')],
      colWidth: [15, 15, 30, 20, 50, 10],
      fileName: t('专用业务 + 地域 + 机型（硬盘）'),
    },
  };

  const generateData = () => {
    switch (props.dimension) {
      case 'spec':
        return props.data.map((item) => [
          item.for_biz_name,
          item.city,
          item.spec_type_display,
          item.spec_name,
          item.sub_zone_detail_display,
          item.count,
        ]);
      case 'device_class':
        return props.data.map((item) => [
          item.for_biz_name,
          item.city,
          item.device_display,
          item.cpu_mem_summary,
          item.sub_zone_detail_display,
          item.count,
        ]);
      default:
        return [];
    }
  };

  const handleClick = () => {
    const workbook = XLSX.utils.book_new();
    const { header, colWidth, fileName } = configMap[props.dimension as keyof typeof configMap];
    const data = generateData();
    const worksheet = XLSX.utils.aoa_to_sheet([header, ...data]);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Sheet1');
    worksheet['!cols'] = colWidth.map((width) => ({ wch: width }));
    const timestamp = new Date().getTime();
    XLSX.writeFile(workbook, `${fileName}_${timestamp}.xlsx`);
  };
</script>

<style lang="less" scoped>
  .export-excel {
    display: flex;
    font-size: 12px;
    color: #3a84ff;
    align-items: center;
    cursor: pointer;
  }
</style>
