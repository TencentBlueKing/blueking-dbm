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
  <div class="add-nodes">
    <NodeNumber :id="id" />
    <DbForm
      ref="formRef"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('资源规格')"
        property="spec_id"
        required>
        <SpecSelector
          ref="specRef"
          v-model="formData.spec_id"
          :biz-id="currentBizId"
          :cloud-id="cloudId"
          :cluster-type="ClusterTypes.RIAK"
          machine-type="riak"
          style="width: 100%;" />
      </BkFormItem>
      <BkFormItem
        :label="t('节点数量')"
        property="count"
        required>
        <BkInput
          v-model="formData.count"
          class="mb10"
          clearable
          :max="100"
          :min="1"
          type="number" />
      </BkFormItem>
    </DbForm>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import SpecSelector from '@components/apply-items/SpecSelector.vue';

  import NodeNumber from './components/NodeNumber.vue';

  interface Props {
    id: number,
    cloudId: number
  }

  interface Emits {
    (e: 'submitSuccess'): void
  }

  interface Expose {
    submit: () => Promise<boolean>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const formRef = ref();
  const formData = reactive({
    spec_id: '',
    count: 1,
  });

  defineExpose<Expose>({
    async submit() {
      await formRef.value.validate();

      return new Promise((resolve, reject) => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_SCALE_OUT,
          details: {
            ip_source: 'resource_pool',
            cluster_id: props.id,
            resource_spec: {
              riak: formData,
            },
          },

        })
          .then((createTicketResult) => {
            ticketMessage(createTicketResult.id);
            emits('submitSuccess');
            resolve(true);
          })
          .catch(() => reject());
      });
    },
  });
</script>

<style lang="less" scoped>
  .add-nodes {
    padding: 0 40px 24px;
  }
</style>
