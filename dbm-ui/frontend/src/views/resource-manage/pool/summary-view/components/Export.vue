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
    dimension: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const configMap = {
    spec: {
      header: [t('所属业务'), t('地域'), t('规格类型'), t('规格'), t('园区分布（台）'), t('总数（台）')],
      colWidth: [15, 15, 30, 30, 50, 10],
      fileName: t('资源分布统计(地域 + 规格)'),
    },
    device_class: {
      header: [t('所属业务'), t('地域'), t('机型（硬盘）'), t('CPU 内存'), t('园区分布（台）'), t('总数（台）')],
      colWidth: [15, 15, 30, 20, 50, 10],
      fileName: t('资源分布统计(地域 + 机型)'),
    },
  };

  const generateData = () => {
    switch (props.dimension) {
      case 'spec':
        return props.data.map((item) => [
          item.for_biz_name,
          item.city,
          item.specTypeDisplay,
          item.spec_name,
          item.subzoneDetailDisplay,
          item.count,
        ]);
      case 'device_class':
        return props.data.map((item) => [
          item.for_biz_name,
          item.city,
          item.deviceDisplay,
          item.cpu_mem_summary,
          item.subzoneDetailDisplay,
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
    const pad = (num: number) => num.toString().padStart(2, '0');
    const date = new Date();
    const timestamp = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}${pad(date.getHours())}${pad(date.getMinutes())}`;
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
