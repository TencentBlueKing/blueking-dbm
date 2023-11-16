<template>
  <div
    v-if="modelValue"
    v-clickoutside="handleClickOutside"
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
      <RenderTable
        v-slot="slotProps"
        class="mt16">
        <template
          v-for="(item, index) in variableList"
          :key="`${item.name}#${index}`">
          <RenderRow
            v-if="item.name"
            :data="item"
            :is-fixed="slotProps.isOverflow"
            @add="(data: IVariable) => handleAdd(data, index)"
            @remove="handleRemove" />
          <CreateRow
            v-else
            v-model:list="variableList"
            :index="index" />
        </template>
      </RenderTable>
    </div>
    <div
      class="close-btn"
      @click="handleClose">
      <DbIcon type="close" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateVariable } from '@services/openarea';
  import {
    getBizSettingList,
  } from '@services/system-setting';

  import { useGlobalBizs } from '@stores';

  import {
    messageSuccess,
  } from '@utils';

  import CreateRow from './components/CreateRow.vue';
  import RenderRow from './components/Row.vue';
  import RenderTable from './components/Table.vue';

  export interface IVariable {
    name: string,
    desc: string,
    builtin: boolean,
  }

  const OPEN_AREA_VARS_KEY = 'OPEN_AREA_VARS';

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const modelValue = defineModel<boolean>({
    default: false,
  });
  const variableList = shallowRef<IVariable[]>([]);

  const {
    loading: isLoading,
    run: fetchVariableList,
  } = useRequest(getBizSettingList, {
    manual: true,
    onSuccess(data) {
      variableList.value = _.sortBy(data[OPEN_AREA_VARS_KEY], item => !item.builtin);
    },
  });

  const {
    // loading: isSubmiting,
    run: deleteVariableMethod,
  } = useRequest(updateVariable<'delete'>, {
    manual: true,
    onSuccess() {
      messageSuccess(t('删除成功'));
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

  const handleClickOutside = () => {
    modelValue.value = false;
  };

  const handleAdd = (variable: IVariable, index: number) => {
    const lastVariableList = [...variableList.value];
    lastVariableList.splice(index + 1, 0, variable);
    variableList.value = lastVariableList;
  };

  const handleRemove = (variable: IVariable) => {
    deleteVariableMethod({
      op_type: 'delete',
      old_var: {
        ...variable,
      },
      new_var: undefined,
    });
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
    z-index: 99;
    width: 600px;
    background-color: #fff;
    box-shadow: -1px 0 0 0 #DCDEE5;

    .bk-table{
      .bk-table-body{
        tr{
          .copy-btn{
            cursor: pointer;
            opacity: 0%;
          }

          &:hover{
            .copy-btn{
              color: #3a84ff;
              opacity: 100%;
              transition: 0.1s;
            }
          }
        }
      }
    }

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

        &.is-disabled{
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
