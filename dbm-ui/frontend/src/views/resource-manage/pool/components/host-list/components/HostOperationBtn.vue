<template>
  <BkPopConfirm
    ext-cls="content-wrapper"
    :title="props.title"
    trigger="click"
    width="360"
    @confirm="handleConfirm">
    <BkButton
      :class="btnCls"
      text
      theme="primary">
      {{ buttonText }}
    </BkButton>
    <template #content>
      <section class="content">
        <div>
          <span>{{ t('主机') }}：</span>
          <span class="ip">{{ props.data.ip }}</span>
        </div>
        <div class="tip">{{ props.tip }}</div>
      </section>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { type DeleteEvent, removeResource } from '@/services/source/dbresourceResource';

  interface Props {
    title: string;
    buttonText: string;
    tip: string;
    btnCls?: string;
    data: DbResourceModel;
    type: DeleteEvent;
    refresh: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { run } = useRequest(removeResource, {
    manual: true,
    onSuccess: () => {
      Message({
        theme: 'success',
        message: t('操作成功'),
      });
      props.refresh();
    },
  });

  const handleConfirm = () => {
    run({
      bk_host_ids: [props.data.bk_host_id],
      event: props.type,
    });
  };
</script>

<style lang="less">
  .content-wrapper {
    .content {
      font-size: 12px;
      color: #63656e;

      .ip {
        color: #313238;
      }

      .tip {
        margin-top: 4px;
        margin-bottom: 14px;
      }
    }

    .bk-pop-confirm-title {
      font-size: 16px !important;
      color: #313238 !important;
    }
  }
</style>
