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

  import { exportExcelFile } from '@utils';

  import type { IValue } from '../Index.vue';

  interface Props {
    data: {
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    dbIgnoreName: string[];
    dbName: string[];
    renameInfoList: IValue[];
  }>({
    required: true,
  });

  const { t } = useI18n();
  // 导出文件
  const handleExport = () => {
    const formatData = modelValue.value.renameInfoList.map((item) => ({
      [t('已存在的 DB')]: item.rename_db_name,
      [t('构造 DB 名称')]: item.db_name,
      [t('构造后 DB 名称')]: item.target_db_name,
    }));
    const colsWidths = [{ width: 40 }, { width: 40 }, { width: 40 }];

    exportExcelFile(
      formatData,
      colsWidths,
      `集群（${props.data.srcCluster.id}）`,
      `${t('SQLServer定点回档手动修改回档DB名')}_${props.data.srcCluster.id}.xlsx`,
    );
  };
</script>
