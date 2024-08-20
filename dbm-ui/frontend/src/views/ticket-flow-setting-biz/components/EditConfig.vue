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
    v-model:isShow="isShow"
    placement="top"
    :title="t('修改目标')"
    trigger="manual"
    width="600"
    @cancel="isShow = false"
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
        <RenderTarget
          ref="targetRef"
          v-model="targetData"
          class="form-target-box" />
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { updateTicketFlowConfig } from '@services/source/ticket';

  import { DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  import RenderTarget from './render-target/Index.vue';

  interface Props {
    data: TicketFlowDescribeModel;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const targetRef = ref<InstanceType<typeof RenderTarget>>();

  const targetData = computed(() => ({
    dbType: (props.data.group as DBTypes) || DBTypes.MYSQL,
    bizId: props.data.bk_biz_id || 0,
    clusterIds: props.data.cluster_ids || [],
  }));

  const { run: updateTicketFlowConfigRun } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess: (data) => {
      if (!data) {
        isShow.value = false;
        messageSuccess(t('操作成功'));
        emits('success');
      }
    },
  });

  const handleConfirm = async () => {
    const targetData = await targetRef.value!.getValue();
    const params = {
      ...targetData,
      ticket_types: [props.data.ticket_type],
      configs: {
        need_manual_confirm: props.data.configs.need_manual_confirm,
        need_itsm: props.data.configs.need_itsm,
      },
      config_ids: [props.data.id],
    };
    updateTicketFlowConfigRun(params);
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

    .form-target-box {
      margin: 18px;
    }
  }
</style>
