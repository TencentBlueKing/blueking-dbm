<template>
  <div class="cell-name-box">
    <TableEditInput
      ref="inputRef"
      v-model="modelValue"
      :style="{
        opacity: isEditing ? 1 : 0
      }"
      @submit="handleEditSubmit" />
    <div
      v-if="!isEditing"
      class="value-text"
      @click="handleEdit">
      {{ modelValue }}
      <DbIcon
        v-bk-tooltips="t('复制变量')"
        class="ml-4 copy-btn"
        type="copy"
        @click.stop="handleCopy" />
    </div>
    <div
      v-if="isSubmiting"
      class="submit-loading rotate-loading">
      <DbIcon
        svg
        type="sync-pending" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateVariable } from '@services/openarea';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import {
    execCopy,
    messageSuccess,
  } from '@utils';

  import type { IVariable } from '../Index.vue';

  interface Props {
    data: IVariable
  }

  const props = defineProps<Props>();
  const emits = defineEmits<{
    'edit-change': []
  }>();

  const modelValue = defineModel<string>({
    default: '',
    required: true,
    local: true,
  });
  const { t } = useI18n();


  const inputRef = ref<InstanceType<typeof TableEditInput>>();
  const isEditing = ref(false);

  const {
    loading: isSubmiting,
    run: updateVariableMethod,
  } = useRequest(updateVariable<'update'>, {
    manual: true,
    onSuccess() {
      messageSuccess(t('编辑成功'));
      isEditing.value = false;
      emits('edit-change');
    },
  });

  const handleEdit = () => {
    isEditing.value = true;
    (inputRef.value as InstanceType<typeof TableEditInput>).focus();
  };

  const handleEditSubmit = () => {
    updateVariableMethod({
      op_type: 'update',
      new_var: {
        ...props.data,
        name: modelValue.value,
      },
      old_var: {
        ...props.data,
      },
    });
  };

  const handleCopy = () => {
    execCopy(modelValue.value);
  };
</script>
<style lang="less" scoped>
  .cell-name-box{
    position: relative;

    .value-text{
      position: absolute;
      top: 1px;
      right: 16px;
      left: 16px;
      display: flex;
      overflow: hidden;
      line-height: 40px;
      text-overflow: ellipsis;
      cursor: pointer;
      background: #fff;
      align-items: center;

      &:hover{
        .copy-btn{
          color: #3a84ff;
          opacity: 100%;
          transition: 0.1s;
        }
      }

      .copy-btn{
        padding: 5px;
        opacity: 0%;
      }
    }

    .submit-loading{
      position: absolute;
      top: 0;
      right: 10px;
      bottom: 0;
      display: flex;
      align-items: center;
      color: #3a84ff;
    }
  }
</style>
