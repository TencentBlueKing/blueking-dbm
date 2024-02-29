<template>
  <div style="padding: 20px 16px">
    <BkTable
      :columns="columns"
      :data="data.config_rules" />
  </div>
  <BkDialog
    v-model:is-show="isShowPermissionRule"
    :title="t('共 n 条权限规则【c】', { n: currentPrivData.length, c: 'asdas' })"
    :width="950">
    <PrivRuleDetail
      :cluster-id="clusterId"
      :rule-id-list="currentPrivData" />
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';

  import PrivRuleDetail from './components/PrivRuleDetail.vue';

  interface Props {
    clusterId: number,
    data: OpenareaTemplateModel
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isShowPermissionRule = ref(false);
  const currentPrivData = shallowRef<number[]>([]);

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
          theme="primary"
          onClick={() => handleShowPermissioinRule(data.priv_data)}>
          {t('n个规则', { n: data.priv_data.length })}
        </bk-button>
      ),
    },
  ];

  const handleShowPermissioinRule = (data: number[]) => {
    isShowPermissionRule.value = true;
    currentPrivData.value = data;
  };

  const handleClose = () => {
    isShowPermissionRule.value = false;
  };
</script>
