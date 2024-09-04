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
  <BkPopConfirm
    :confirm-text="t('删除')"
    placement="top"
    :title="t('确认删除该类型配置？')"
    trigger="click"
    width="270"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="delete-config-content">
        <div class="form-item">
          <div class="form-item-label">{{ t('单据类型') }}：</div>
          <div class="form-item-text">
            {{ data.ticket_type_display }}
          </div>
        </div>
        <div class="form-item">{{ t('删除后，将不可恢复，请谨慎操作！') }}</div>
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { deleteTicketFlowConfig } from '@services/source/ticket';

  import { messageSuccess } from '@utils';

  interface Props {
    data: TicketFlowDescribeModel;
  }

  interface Emits {
    (e: 'success'): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number>({
    default: [],
  });

  const { t } = useI18n();

  const { run: deleteTicketFlowConfigRun } = useRequest(deleteTicketFlowConfig, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const handleConfirm = () => {
    deleteTicketFlowConfigRun({
      config_ids: [modelValue.value],
    });
  };
</script>

<style lang="less" scoped>
  .delete-config-content {
    margin-bottom: 24px;
    color: #63656e;

    .form-item {
      display: flex;
      width: 100%;
      line-height: 22px;

      .form-item-label {
        width: 60px;
      }

      .form-item-text {
        height: auto;
        color: #313238;
        flex: 1;
      }
    }
  }
</style>
