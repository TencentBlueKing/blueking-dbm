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
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@components/tools-table-input/index.vue';

  import {
    execCopy,
  } from '@utils';

  const { t } = useI18n();

  const modelValue = defineModel<string>({
    required: false,
    default: '',
    local: true,
  });

  const inputRef = ref<InstanceType<typeof TableEditInput>>();
  const isEditing = ref(false);

  const handleEdit = () => {
    isEditing.value = true;
    (inputRef.value as InstanceType<typeof TableEditInput>).focus();
  };

  const handleEditSubmit = () => {
    isEditing.value = false;
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
  }
</style>
