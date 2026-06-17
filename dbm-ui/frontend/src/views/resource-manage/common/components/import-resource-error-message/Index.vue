<template>
  <BkDialog
    v-model:is-show="modelValue"
    class="import-resource-error-message"
    :show-mask="false"
    theme="primary"
    width="900">
    <template #header>
      <div class="import-resource-error-message-header">
        <DbIcon
          class="mr-4"
          type="exclamation-fill" />
        <span class="header-title">
          {{ t('以下 n 台主机校验不通过，请确认机器情况或清除有问题的机器后重新导入', { n: ips.length }) }}
        </span>
        <BkButton
          class="header-copy"
          text
          theme="primary"
          @click="handleCopyIps">
          <DbIcon
            class="mr-4"
            type="copy" />
          <span>{{ t('复制 IP') }}</span>
        </BkButton>
      </div>
    </template>
    <div class="import-resource-error-message-content">
      <div
        v-for="(item, index) in messageList"
        :key="index"
        class="content-item">
        <div class="content-item-title">• {{ item.message }}（{{ item.ips.length }}{{ t('台') }}）</div>
        <BkOverflowTitle
          class="content-item-ips"
          type="tips">
          {{ item.ips.join(',') }}
        </BkOverflowTitle>
      </div>
    </div>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  interface Props {
    ips: string[];
    messageList: {
      ips: string[];
      message: string;
    }[];
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();

  const handleCopyIps = () => {
    execCopy(props.ips.join('\n'), t('复制成功，共n条', { n: props.ips.length }));
  };
</script>

<style lang="less">
  .import-resource-error-message {
    .bk-modal-wrapper {
      top: 30px !important;
      transform: translate(-50%, 0);
    }

    .bk-modal-body {
      background: var(--message-danger-bg-color);
      border: 1px solid var(--message-danger-border-color);
      box-shadow: 0 2px 4px 0 var(--message-danger-shadow-color);
    }

    .bk-dialog-header {
      padding: 4px 36px 0 12px;
    }

    .bk-dialog-content {
      padding: 0 24px 8px 12px;
      margin: 0;
    }

    .bk-modal-footer {
      display: none;
    }

    .bk-modal-close {
      &:hover {
        background-color: transparent;
      }
    }

    .import-resource-error-message-header {
      display: flex;
      align-items: center;
      width: 100%;
      font-size: 14px;
      color: #ea3636;

      .header-title {
        font-weight: bolder;
      }

      .header-copy {
        margin-left: auto;
      }
    }

    .import-resource-error-message-content {
      .content-item {
        margin-top: 16px;
        font-size: 12px;
        color: #4d4f56;

        .content-item-title {
          margin-left: 2px;
          font-weight: bolder;
        }

        .content-item-ips {
          margin-top: 8px;
          margin-left: 12px;
        }
      }
    }
  }
</style>
