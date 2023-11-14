<template>
  <div style="padding: 20px 16px;">
    <BkTable
      :columns="columns"
      :data="data.config_rules" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';

  interface Props {
    data: OpenareaTemplateModel
  }

  defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('克隆 DB'),
      field: 'source_db',
    },
    {
      label: t('克隆表结构'),
      render: ({ data }: {data: OpenareaTemplateModel['config_rules'][0]}) => (
        <>
          {
            data.schema_tblist.map(item => (
                <bk-tag>{item}</bk-tag>
            ))
          }
        </>
      ),
    },
    {
      label: t('克隆表数据'),
      render: ({ data }: {data: OpenareaTemplateModel['config_rules'][0]}) => (
        <>
          {
            data.data_tblist.map(item => (
                <bk-tag>{item}</bk-tag>
            ))
          }
        </>
      ),
    },
    {
      label: t('生成目标 DB 范式'),
      field: 'target_db_pattern',
    },
    {
      label: t('初始化授权'),
      render: ({ data }: {data: OpenareaTemplateModel['config_rules'][0]}) => (
        <bk-button
          text
          theme="primary">
          {t('n个规则', { n: data.priv_data.length })}
        </bk-button>
      ),
    },
  ];
</script>
