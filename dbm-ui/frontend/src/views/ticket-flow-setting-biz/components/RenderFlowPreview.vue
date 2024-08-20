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
    placement="top"
    :title="t('确认xx“单据审批”流程节点？', [modelValue ? t('删除') : t('添加')])"
    trigger="click"
    width="400"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="ticket-flow-content">
        <div class="form-item">
          <div class="form-item-label">{{ t('单据类型') }}：</div>
          <div
            class="form-item-text"
            style="color: #313238">
            {{ data.ticket_type_display }}
          </div>
        </div>
        <div class="form-item mb-16 mt-6">
          <div class="form-item-label">{{ t('流程预览') }}：</div>
          <div class="form-item-text">
            <span
              v-for="(item, index) in localFlow"
              :key="index">
              <span v-if="index !== 0"> -> </span>
              <span :class="item.type">{{ item.text }}</span>
            </span>
          </div>
        </div>
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { updateTicketFlowConfig } from '@services/source/ticket';

  import { messageSuccess } from '@utils';

  interface Props {
    data: TicketFlowDescribeModel;
    configKey: keyof TicketFlowDescribeModel['configs'];
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();

  const configsMap = {
    need_itsm: t('单据审批'),
    need_manual_confirm: t('人工确认'),
  };

  const localFlow = computed(() => {
    const currentNodeText = configsMap[props.configKey];
    const results = props.data.flow_desc.map((text) => ({
      text,
      type: text === currentNodeText && modelValue.value ? 'delete' : '',
    }));
    if (!modelValue.value) {
      results.unshift({
        text: currentNodeText,
        type: 'add',
      });
    }
    return results;
  });

  const { run: updateTicketFlowConfigRun } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess: (data) => {
      if (!data) {
        messageSuccess(t('操作成功'));
        emits('success');
      }
    },
  });

  const handleConfirm = () => {
    const params = {
      bk_biz_id: props.data.bk_biz_id,
      cluster_ids: props.data.cluster_ids,
      ticket_types: [props.data.ticket_type],
      configs: {
        ...props.data.configs,
        [props.configKey]: !modelValue.value,
      },
      config_ids: [props.data.id],
    };
    updateTicketFlowConfigRun(params);
  };
</script>

<style lang="less" scoped>
  .ticket-flow-content {
    .form-item {
      display: flex;
      width: 100%;

      .form-item-label {
        width: 60px;
      }

      .form-item-text {
        flex: 1;
        height: auto;

        .add {
          color: #ff9c01;
        }

        .delete {
          color: #ea3636;
          text-decoration: line-through;
        }
      }
    }
  }
</style>
