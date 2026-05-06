<template>
  <div
    class="rich-text-edit-value-main"
    :class="{ 'is-only-view': readonly }">
    <div class="display-mian">
      <RiskMemoEditor
        :key="riskId"
        v-model="localValue"
        class="editor-main"
        :readonly="readonly" />
      <AuthTemplate
        v-if="readonly"
        action-id="risk_memo_manage"
        :biz-id="bizId"
        :permission="managePermission">
        <DbIcon
          class="edit-main"
          type="edit"
          @click="handleClickEdit" />
      </AuthTemplate>
    </div>
    <div
      v-if="!readonly"
      class="operate-btn-main">
      <BkButton
        v-bk-tooltips="{
          disabled: !isEditorEmpty,
          content: t('不能为空'),
        }"
        class="w-88"
        :disabled="isEditorEmpty"
        :loading="updateLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleClickCancel">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateRiskMemo } from '@services/source/riskMemo';

  import { messageSuccess } from '@utils';

  import RiskMemoEditor from '../../../../RickMemoEditor.vue';

  interface Props {
    bizId?: number;
    managePermission?: boolean;
    riskId?: number;
    value?: string;
  }

  type Emits = (e: 'updateSuccess') => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: 0,
    managePermission: true,
    riskId: 0,
    value: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref('');
  const readonly = ref(false);

  const isEditorEmpty = computed(() => localValue.value === '<p><br></p>');

  const { loading: updateLoading, run: runUpdateRiskMemoRun } = useRequest(updateRiskMemo, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('更新成功'));
      emits('updateSuccess');
      readonly.value = true;
    },
  });

  watch(
    () => props.riskId,
    () => {
      if (props.riskId) {
        readonly.value = true;
      }
    },
    {
      immediate: true,
    },
  );

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
    readonly.value = false;
  };

  const handleSubmit = () => {
    runUpdateRiskMemoRun({
      description: localValue.value,
      id: props.riskId,
    });
  };

  const handleClickCancel = () => {
    readonly.value = true;
    localValue.value = props.value;
  };
</script>
<style lang="less">
  .rich-text-edit-value-main {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    font-size: 12px;

    &.is-only-view {
      .db-editor-main {
        background: #f5f7fa;
        padding: 16px;
        border-radius: 8px;
      }
    }

    .display-mian {
      display: flex;
      width: 100%;

      .editor-main {
        max-width: calc(100% - 20px);
      }

      .edit-main {
        display: block;
        margin-top: 4px;
        margin-left: 4px;
        font-size: 12px;
        color: #979ba5;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .operate-btn-main {
      display: flex;
      margin-top: 12px;
      gap: 8px;
    }
  }
</style>
