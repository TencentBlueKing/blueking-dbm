<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSideslider
    :before-close="handleClose"
    :is-show="isShow"
    :width="1100"
    @closed="handleClose">
    <template #header>
      <div class="header-main">
        {{ t('追加订阅【name】', {name: data?.name}) }}
      </div>
    </template>
    <div class="append-rule-edit-box">
      <BkForm
        ref="formRef"
        class="edit-form"
        form-type="vertical">
        <BkFormItem
          :label="t('数据源与接收端配置')"
          required>
          <ReceiverData ref="receiverDataRef" />
        </BkFormItem>
        <BkFormItem
          :label="t('Dumper部署位置')"
          required>
          <BkRadio
            v-model="deployPlace"
            class="deploy-place-radio"
            disabled
            label="master">
            {{ t('集群Master所在主机') }}
          </BkRadio>
        </BkFormItem>
        <BkFormItem
          :label="t('数据同步方式')"
          required>
          <BkRadioGroup v-model="syncType">
            <BkRadio label="full_sync">
              {{ t('全量同步') }}
            </BkRadio>
            <BkRadio label="incr_sync">
              {{ t('增量同步') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="isSubmitting"
        :loading="isSubmitting"
        theme="primary"
        @click="handleConfirm">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { listDumperConfig } from '@services/source/dumper';
  import { createTicket } from '@services/source/ticket';

  import {
    useBeforeClose,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import ReceiverData from '@views/mysql/dumper/components/create-rule/components/receiver-data/Index.vue';

  interface Props {
    data: DumperConfig | null,
  }

  interface Emits {
    (e: 'success'): void,
    (e: 'cancel'): void,
  }

  type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number]

  const props = withDefaults(defineProps<Props>(), {
    data: null,
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const receiverDataRef = ref();
  const deployPlace = ref('master');
  const syncType = ref('full_sync');
  const isSubmitting = ref(false);

  // 点击确定
  const handleConfirm = async () => {
    if (!props.data) {
      return;
    }
    const infos = await receiverDataRef.value.getValue();
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.TBINLOGDUMPER_INSTALL,
      remark: '',
      details: {
        name: props.data.name,
        add_type: syncType.value,
        repl_tables: props.data.repl_tables,
        infos,
      },
    };
    isSubmitting.value = true;
    try {
      const data = await createTicket(params);
      if (data.id) {
        ticketMessage(data.id);
        emits('success');
        isShow.value = false;
      }
      window.changeConfirm = false;
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleClose = async () => {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    emits('cancel');
    isShow.value = false;
  };

</script>

<style lang="less" scoped>

.header-main {
  display: flex;
  width: 100%;
  overflow: hidden;
  align-items: center;

  .name {
    width: auto;
    max-width: 720px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.append-rule-edit-box {
  display: flex;
  width: 100%;
  padding: 24px 40px;
  flex-direction: column;

  .edit-form {
    // :deep(.bk-form-label) {
    //   font-weight: 700;
    // }

    :deep(.deploy-place-radio) {
      .bk-radio-label {
        color: #63656e;
      }
    }
  }
}


</style>
