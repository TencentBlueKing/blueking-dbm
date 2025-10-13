<template>
  <div
    class="text-edit-value-main"
    :class="{ 'is-error': isError }">
    <div
      v-if="!isEdit"
      class="display-mian">
      <div class="value-display">
        {{ localValue }}
      </div>
      <AuthTemplate
        v-if="!readonly"
        action-id="risk_memo_manage"
        :biz-id="bizId"
        :permission="managePermission">
        <DbIcon
          class="edit-main"
          type="edit"
          @click="handleClickEdit" />
      </AuthTemplate>
    </div>
    <BkInput
      v-else
      ref="editValueRef"
      v-model="localValue"
      :autosize="{
        minRows: 3,
        maxRows: 22,
      }"
      class="value-edit-main"
      :maxlength="500"
      :resize="false"
      :type="textArea ? 'textarea' : 'input'"
      @blur="handleBlur"
      @enter="handleEnter"
      @input="handleInput" />
    <DbIcon
      v-if="isError"
      v-bk-tooltips="t('不能为空')"
      class="error-icon"
      type="exclamation-fill" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    bizId?: number;
    managePermission?: boolean;
    readonly?: boolean;
    textArea?: boolean;
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: 0,
    managePermission: true,
    readonly: false,
    textArea: false,
    value: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editValueRef = ref<any>(null);
  const isEdit = ref(false);
  const localValue = ref('');
  const isError = ref(false);

  watch(
    () => props.value,
    () => {
      localValue.value = props.value;
    },
    {
      immediate: true,
    },
  );

  const handleClickEdit = () => {
    isEdit.value = true;
    setTimeout(() => {
      editValueRef.value?.focus();
    });
  };

  const handleInput = () => {
    isError.value = false;
  };

  const handleBlur = () => {
    if (!localValue.value) {
      isError.value = true;
      return;
    }
    if (props.value !== localValue.value) {
      emits('change', localValue.value);
    }
    isEdit.value = false;
  };

  const handleEnter = () => {
    if (!props.textArea) {
      handleBlur();
    }
  };
</script>
<style lang="less">
  .text-edit-value-main {
    position: relative;
    display: flex;
    width: 100%;
    font-size: 12px;
    align-items: center;

    &.is-error {
      .value-edit-main {
        border-color: #ea3636;
      }
    }

    .display-mian {
      display: flex;
      width: 100%;
      align-items: center;
      margin-top: -3px;

      &:hover {
        .edit-main {
          display: block;
        }
      }

      .value-display {
        flex: 0 1 auto;
        max-width: calc(100% - 20px);
        line-height: 20px;
        overflow-wrap: break-word;
      }

      .edit-main {
        display: none;
        width: 12px;
        height: 12px;
        margin-left: 4px;
        font-size: 12px;
        color: #979ba5;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .value-edit-main {
      width: 100%;
    }

    .error-icon {
      position: absolute;
      top: 50%;
      right: 8px;
      font-size: 14px;
      color: #ea3636;
      cursor: pointer;
      transform: translateY(-50%);
    }
  }
</style>
