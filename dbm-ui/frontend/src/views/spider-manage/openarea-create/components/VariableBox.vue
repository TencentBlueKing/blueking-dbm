<template>
  <div
    v-if="modelValue"
    class="openarea-variable-box">
    <div class="title">
      {{ t('变量') }}
    </div>
    <div
      v-bkloading="{isLoading}"
      class="wrapper">
      <BkAlert
        class="mb-16"
        :title="t('可以在命名范式与 xxx 中使用')" />
      <BkTable
        :columns="talbeColumns"
        :data="variableList" />
    </div>
    <div
      class="close-btn"
      @click="handleClose">
      <DbIcon type="close" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import {
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizSettingList } from '@services/system-setting';

  import { useGlobalBizs } from '@stores';

  interface IVariable {
    name: string,
    desc: string
  }

  const OPEN_AREA_VARS_KEY = 'OPEN_AREA_VARS';

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const modelValue = defineModel<boolean>({
    default: false,
  });
  const variableList = shallowRef<IVariable[]>([]);

  const talbeColumns = [
    {
      label: t('变量名'),
      field: 'name',
    },
    {
      label: t('说明'),
      field: 'desc',
    },
    {
      label: t('类型'),
      width: 80,
      render: () => 'string',
    },
    {
      label: t('操作'),
      width: 80,
      render: ({ data }: {data: IVariable}) => (
        <>
          <div class="action-btn">
            <db-icon
              type="plus-fill"
              onClick={() => handleAdd(data)} />
          </div>
          <div class="action-btn">
            <db-icon
              class="ml-16"
              type="minus-fill"
              onClick={() => handleRemove(data)} />
          </div>
        </>
      ),
    },
  ];

  const {
    loading: isLoading,
    run: fetchVariableList,
  } = useRequest(getBizSettingList, {
    manual: true,
    onSuccess(data) {
      variableList.value = data[OPEN_AREA_VARS_KEY];
    },
  });

  watch(modelValue, () => {
    if (modelValue.value) {
      fetchVariableList({
        bk_biz_id: currentBizId,
        key: OPEN_AREA_VARS_KEY,
      });
    }
  });

  const handleAdd = (variable: IVariable) => {
    console.log(variable);
  };

  const handleRemove = (variable: IVariable) => {
    console.log(variable);
  };

  const handleClose = () => {
    modelValue.value = false;
  };
</script>
<style lang="less">
  .openarea-variable-box {
    position: fixed;
    top: 104px;
    right: 0;
    bottom: 0;
    width: 600px;
    background-color: #fff;
    box-shadow: -1px 0 0 0 #DCDEE5;

    .title{
      display: flex;
      height: 52px;
      padding-left: 24px;
      box-shadow: inset 0 -1px 0 0 #DCDEE5;
      align-items: center;
    }

    .wrapper{
      padding: 16px;

      .action-btn{
        display: inline-flex;
        font-size: 14px;
        color: #c4c6cc;
        cursor: pointer;
        transition: all .15s;

        &:hover{
          color: #979ba5;
        }

        &.disbled{
          color: #dcdee5;
          cursor: not-allowed;
        }
      }
    }

    .close-btn{
      position: absolute;
      top: 5px;
      right: 5px;
      display: flex;
      width: 26px;
      height: 26px;
      font-size: 22px;
      color: #979ba5;
      cursor: pointer;
      border-radius: 50%;
      align-items: center;
      justify-content: center;

      &:hover{
        background-color: #f0f1f5;
      }
    }
  }
</style>
