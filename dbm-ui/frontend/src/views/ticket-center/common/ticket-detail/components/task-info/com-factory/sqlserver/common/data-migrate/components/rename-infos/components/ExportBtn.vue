<template>
  <BkButton
    class="ml-12"
    text
    theme="primary"
    @click="handleExport">
    <DbIcon
      class="mr-4"
      type="daochu-2" />
    {{ t('导出') }}
  </BkButton>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { exportExcelFile } from '@utils';

  interface Props {
    data: TicketModel<Sqlserver.DataMigrate>['details']['infos'][number];
    domain: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  // 导出文件
  const handleExport = () => {
    const formatData = props.data.rename_infos.map((item) => ({
      [t('已存在的 DB')]: item.rename_db_name,
      [t('迁移 DB 名称')]: item.db_name,
      [t('迁移后 DB 名称')]: item.target_db_name,
    }));
    const colsWidths = [{ width: 40 }, { width: 40 }, { width: 40 }];

    exportExcelFile(
      formatData,
      colsWidths,
      `集群（${props.domain}）`,
      `${t('SQLServer数据迁移手动修改迁移DB名')}_${props.domain}.xlsx`,
    );
  };
</script>
