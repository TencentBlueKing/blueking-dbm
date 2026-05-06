<template>
  <div class="add-follow-up-main">
    <AuthButton
      v-if="!showEdit"
      v-bk-tooltips="{
        disabled: !managePermission || !isRiskDone,
        content: t('已结项的风险，不能添加跟进'),
      }"
      action-id="risk_memo_manage"
      :biz-id="bizId"
      :disabled="isRiskDone"
      :permission="managePermission"
      text
      theme="primary"
      @click="handleAddFollowUp">
      <DbIcon
        style="font-size: 14px"
        type="plus-fill" />
      <span
        class="ml-4"
        style="font-size: 12px">
        {{ t('添加') }}
      </span>
    </AuthButton>
    <div
      v-else
      class="edit-follow-up-main">
      <RiskMemoEditor v-model="editorHtml" />
      <div class="operate-btn-main">
        <BkButton
          v-bk-tooltips="{
            disabled: !isEditorEmpty,
            content: t('请先输入跟进内容'),
          }"
          class="w-88"
          :disabled="isEditorEmpty"
          :loading="addLoading"
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
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { filterXss } from '@blueking/xss-filter';

  import { createRiskFollowUp } from '@services/source/riskMemo';

  import RiskMemoEditor from '../../RickMemoEditor.vue';

  interface Props {
    bizId?: number;
    isRiskDone?: boolean;
    managePermission?: boolean;
    riskId: number;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: 0,
    isRiskDone: false,
    managePermission: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const showEdit = ref(false);
  const editorHtml = ref('');

  const isEditorEmpty = computed(() => editorHtml.value === '<p><br></p>');

  const { loading: addLoading, run: runCreateRiskFollowUp } = useRequest(createRiskFollowUp, {
    manual: true,
    onSuccess: () => {
      editorHtml.value = '';
      emits('success');
      showEdit.value = false;
    },
  });

  const handleAddFollowUp = () => {
    showEdit.value = true;
  };

  const handleClickCancel = () => {
    showEdit.value = false;
  };

  const handleSubmit = () => {
    runCreateRiskFollowUp({
      content: filterXss(editorHtml.value, {
        imgSrcMode: 'none',
      }),
      risk: props.riskId,
    });
  };
</script>
<style lang="less">
  .add-follow-up-main {
    .edit-follow-up-main {
      .operate-btn-main {
        display: flex;
        align-items: center;
        margin-top: 12px;
        gap: 8px;
      }
    }
  }
</style>
