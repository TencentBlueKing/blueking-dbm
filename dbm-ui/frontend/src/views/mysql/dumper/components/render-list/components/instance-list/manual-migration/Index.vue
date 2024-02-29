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
        {{ t('Dumper 手动迁移【name】', { name: `${data.ip}:${data.listen_port}` }) }}
      </div>
    </template>
    <div class="append-rule-edit-box">
      <div class="info-title">
        {{ t('待迁移确认信息') }}
      </div>
      <div class="basic-info-box">
        <div class="info-item">
          <div class="title">{{ t('Dumper实例') }}：</div>
          <div
            v-overflow-tips
            class="content">
            {{ `${data.ip}:${data.listen_port}` }}
          </div>
        </div>
        <div class="info-item">
          <div class="title">{{ t('数据源集群') }}：</div>
          <div
            v-overflow-tips
            class="content">
            {{ data.source_cluster.immute_domain ?? '--' }}
          </div>
        </div>
        <div class="info-item">
          <div class="title">{{ t('Dumper版本') }}：</div>
          <div
            v-overflow-tips
            class="content">
            {{ data.version }}
          </div>
        </div>
        <div class="info-item">
          <div class="title">Dumper ID：</div>
          <div
            v-overflow-tips
            class="content">
            {{ data.dumper_id }}
          </div>
        </div>
        <div class="info-item">
          <div class="title">{{ t('接收端类型') }}：</div>
          <div
            v-overflow-tips
            class="content">
            {{ data.protocol_type }}
          </div>
        </div>
        <div class="info-item">
          <div class="title">{{ t('接收端集群与端口') }}：</div>
          <div
            v-overflow-tips
            class="content">
            {{ `${data.target_address}:${data.target_port}` }}
          </div>
        </div>
      </div>
      <div class="info-title mb-16">
        {{ t('迁移目标信息') }}
      </div>
      <BkForm
        ref="formRef"
        class="edit-form"
        form-type="vertical"
        :model="formModel"
        :rules="formRules">
        <BkFormItem
          :label="t('迁移目标位置')"
          required>
          <BkInput
            disabled
            :value="targetPos" />
        </BkFormItem>
        <BkFormItem
          label="binlog file"
          property="binlog_file"
          required>
          <BkInput v-model="formModel.binlog_file" />
        </BkFormItem>
        <BkFormItem
          :label="t('binlog pos')"
          property="binlog_pos"
          required>
          <BkInput
            v-model="formModel.binlog_pos"
            :min="1"
            type="number" />
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

  import DumperInstanceModel from '@services/model/dumper/dumper';
  import { createTicket } from '@services/source/ticket';

  import { useBeforeClose, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  interface Props {
    data: DumperInstanceModel;
  }

  interface Emits {
    (e: 'success'): void;
    (e: 'cancel'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();

  const targetPos = computed(
    () =>
      `${props.data.source_cluster.master_ip}:${props.data.source_cluster.master_port} ( ${props.data.source_cluster.immute_domain} )`,
  );

  const handleBeforeClose = useBeforeClose();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const formRef = ref();
  const isSubmitting = ref(false);

  const formModel = reactive({
    binlog_file: '',
    binlog_pos: '',
  });

  const formRules = {
    binlog_file: [
      {
        validator: (value: string) => Boolean(value),
        message: t('不能为空'),
        trigger: 'blur',
      },
    ],
    binlog_pos: [
      {
        validator: (value: string) => Boolean(value),
        message: t('不能为空'),
        trigger: 'blur',
      },
    ],
  };

  const handleConfirm = async () => {
    await formRef.value.validate();
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.TBINLOGDUMPER_SWITCH_NODES,
      remark: '',
      details: {
        is_safe: true,
        infos: [
          {
            cluster_id: props.data.source_cluster.id,
            switch_instances: [
              {
                dumper_instance_id: props.data.id,
                host: props.data.source_cluster.master_ip,
                port: props.data.source_cluster.master_port,
                repl_binlog_file: formModel.binlog_file,
                repl_binlog_pos: formModel.binlog_pos,
              },
            ],
          },
        ],
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

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) {
      return;
    }
    window.changeConfirm = false;
    emits('cancel');
    isShow.value = false;
  }
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

    .info-title {
      font-size: 12px;
      font-weight: 700;
      color: #313238;
    }

    .basic-info-box {
      display: flex;
      width: 100%;
      padding: 30px 70px 18px;
      margin: 8px 0 24px;
      background: #f5f7fa;
      border-radius: 2px;
      flex-wrap: wrap;

      .info-item {
        display: flex;
        width: 50%;
        margin-bottom: 12px;
        font-size: 12px;

        .title {
          width: 110px;
          text-align: right;
        }

        .content {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          flex: 1;
        }
      }
    }

    .edit-form {
      :deep(.deploy-place-radio) {
        .bk-radio-label {
          color: #63656e;
        }
      }
    }
  }
</style>
