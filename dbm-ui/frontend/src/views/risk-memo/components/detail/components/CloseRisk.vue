<template>
  <BkDialog
    v-model:is-show="isShow"
    class="close-risk-dialog-main"
    quick-close
    :width="480">
    <div class="close-risk-main">
      <div class="main-title">{{ isSpecial ? t('确认将该要求标记为失效?') : t('确认结项该风险?') }}</div>
      <div class="risk-name">
        <div class="title">{{ isSpecial ? t('要求名称') : t('风险名称') }}</div>
        <span class="ml-4 mr-4">:</span>
        <div
          v-overflow-tips
          class="name">
          {{ data?.name || '-' }}
        </div>
      </div>
      <div class="tip-main">
        {{
          isSpecial
            ? t('失效后将无法添加跟进，如仍需添加，后续可以重启规则')
            : t('结项后将无法添加跟进，如仍需添加，后续可以重启风险')
        }}
      </div>
      <BkInput
        v-model="finalContent"
        :maxlength="100"
        :placeholder="isSpecial ? t('请输入失效原因') : t('请输入结项信息')"
        :resize="false"
        type="textarea" />
      <div class="operate-main">
        <BkButton
          class="w-88"
          :disabled="!finalContent"
          :loading="updateLoading"
          theme="primary"
          @click="handleConfirm">
          {{ isSpecial ? t('标记为失效') : t('结项') }}
        </BkButton>
        <BkButton
          class="w-88"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </div>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RiskMemoDetailModel from '@services/model/risk-memo/risk-memo-detail';
  import { updateRiskStatus } from '@services/source/riskMemo';

  interface Props {
    data?: RiskMemoDetailModel;
    isSpecial?: boolean;
  }

  type Emits = (e: 'closeSuccess') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isSpecial: false,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const finalContent = ref('');

  const { loading: updateLoading, run: runUpdateRiskStatus } = useRequest(updateRiskStatus, {
    manual: true,
    onSuccess: () => {
      emits('closeSuccess');
      finalContent.value = '';
      isShow.value = false;
    },
  });

  const handleConfirm = () => {
    runUpdateRiskStatus({
      final_content: finalContent.value,
      risk_id: props.data!.id,
      status: 'done',
    });
  };

  const handleCancel = () => {
    finalContent.value = '';
    isShow.value = false;
  };
</script>
<style lang="less">
  .close-risk-dialog-main {
    .close-risk-main {
      .main-title {
        width: 100%;
        font-size: 20px;
        color: #313238;
        text-align: center;
        margin-bottom: 16px;
      }

      .risk-name {
        font-size: 14px;
        display: flex;

        .title {
          color: #4d4f56;
        }

        .name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: #313238;
        }
      }

      .tip-main {
        margin-top: 16px;
        width: 100%;
        background: #f5f7fa;
        border-radius: 2px;
        padding: 12px 16px;
        margin-bottom: 12px;
      }

      .operate-main {
        width: 100%;
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 18px;
      }
    }

    .bk-dialog-content {
      margin-top: 8px;
    }

    .bk-modal-footer {
      display: none;
    }
  }
</style>
