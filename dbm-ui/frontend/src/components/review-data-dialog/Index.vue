<template>
  <BkDialog
    class="review-data-dialog"
    :is-loading="props.loading"
    :is-show="isShow"
    :title="props.title"
    @closed="handleClose">
    <div class="container">
      <div class="tip">
        {{ props.tip }}
      </div>
      <div class="selected-wrapper">
        <div class="selected-title">
          {{ t('已选择以下') }} <span class="selected-count">{{ props.selected.length }}</span> {{ t('台主机') }}
        </div>
        <div class="selected-content">
          <div
            v-for="item in props.selected"
            :key="item"
            class="selected-item">
            {{ item }}
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <div class="footer">
        <BkButton
          style="width: 88px"
          theme="primary"
          @click="handleConfirm"
          >{{ t('确定') }}</BkButton
        >
        <BkButton
          class="ml-9 operation-btn"
          style="width: 88px"
          @click="handleClose"
          >{{ t('取消') }}</BkButton
        >
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  interface Props {
    title: string;
    tip: string;
    loading: boolean;
    selected: string[];
  }

  interface Emits {
    (e: 'confirm'): void;
    (e: 'cancel'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const handleConfirm = () => {
    emits('confirm');
    isShow.value = false;
  };
  const handleClose = () => {
    emits('cancel');
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .container {
    font-size: 14px;

    .tip {
      background: #f5f6fa;
      border-radius: 2px;
      padding: 12px 16px;
      margin-bottom: 8px;
    }

    .selected-wrapper {
      border: 1px solid #eaebf0;
      border-radius: 2px;
      max-height: 192px;
      overflow-y: auto;

      .selected-title {
        width: 100%;
        padding: 5px 16px;
        background: #f0f1f5;
        color: #313238;
        position: sticky;
        top: 0;

        .selected-count {
          font-weight: 700;
        }
      }

      .selected-content {
        font-size: 12px;

        .selected-item {
          padding: 6px 16px;

          &:nth-child(even) {
            background-color: #fafbfd;
          }

          &:nth-child(odd) {
            background-color: #ffffff;
          }
        }
      }
    }
  }

  .footer {
    display: flex;
    justify-content: center;
  }
</style>

<style lang="less">
  .review-data-dialog {
    .bk-dialog-footer {
      background-color: #fff !important;
      border: none !important;
      padding-top: 0 !important;
      padding-bottom: 24px !important;
    }
  }
</style>
