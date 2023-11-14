<template>
  <div class="openarea-create-config-rule">
    <div class="variable-box">
      <BkButton
        style="margin-bottom: 12px; margin-left: auto; font-size: 12px;"
        text
        theme="primary"
        @click="handleShowVariable">
        {{ t('变量') }}
      </BkButton>
    </div>
    <BkTable
      :columns="tableColumns"
      :data="modelValue" />
  </div>
  <VariableBox v-model="isShowVariable" />
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import VariableBox from '../VariableBox.vue';

  interface IData {
    source_db: string,
    schema_tblist: string[],
    data_tblist: string[],
    target_db_pattern: string,
    priv_data: Record<string, any>
  }

  const { t } = useI18n();

  const modelValue = defineModel<IData[]>({
    default: [{}],
  });

  const isShowVariable = ref(false);


  const tableColumns = [
    {
      label: t('克隆 DB'),
      render: ({ data }: {data: IData}) => {
        console.log(data);
        return (
          <bk-select>
            <bk-option id="asd" name="asdasd" />
          </bk-select>
        );
      },
    },
    {
      label: t('克隆表结构'),
    },
    {
      label: t('克隆表数据'),
    },
    {
      label: t('生成目标 DB 范式'),
    },
    {
      label: t('初始化授权'),
    },
    {
      label: t('操作'),
      width: 120,
    },
  ];

  const handleShowVariable = () => {
    isShowVariable.value = true;
  };
</script>
<style lang="less">
  .openarea-create-config-rule {
    display: block;

    .variable-box{
      display: flex;
      margin-top: -24px;
    }
  }
</style>
