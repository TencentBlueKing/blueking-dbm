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
  <SmartAction>
    <div class="mongo-reduce-shard-page db-toolbox">
      <BkAlert
        class="mb-16"
        theme="info"
        :title="t('缩容分片数：减少分片集群的分片个数，仅支持分片集群；可指定分片或按数量自动选择分片。')" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <BkFormItem
          :label="t('缩容方式')"
          property="reduce_mode"
          required
          style="width: 400px">
          <BkRadioGroup
            v-model="formData.reduce_mode"
            type="card">
            <BkRadioButton label="by_shard_names">
              {{ t('指定分片') }}
            </BkRadioButton>
            <BkRadioButton label="by_count">
              {{ t('指定数量') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <!-- 模式差异表格：动态挂载，模式之间零交叉 -->
        <Component
          :is="modeComponent"
          ref="currentTableRef" />
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ByCountTable from './components/by-count-table/Index.vue';
  import ByShardNamesTable from './components/by-shard-names-table/Index.vue';

  type ReduceMode = 'by_shard_names' | 'by_count';

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    reduce_mode: 'by_shard_names' as ReduceMode,
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.ReduceShard>(TicketTypes.MONGODB_REDUCE_SHARD, {
    onSuccess(ticketDetail) {
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        reduce_mode: ticketDetail.details.infos[0]?.reduce_mode || 'by_shard_names',
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Mongodb.ReduceShard['infos'];
  }>(TicketTypes.MONGODB_REDUCE_SHARD);

  const formRef = useTemplateRef('form');

  const formData = reactive(createDefaultFormData());

  const modeComponentMap = {
    by_count: ByCountTable,
    by_shard_names: ByShardNamesTable,
  };

  const modeComponent = computed(() => modeComponentMap[formData.reduce_mode]);

  const currentTableRef =
    useTemplateRef<ComponentExposed<typeof ByShardNamesTable | typeof ByCountTable>>('currentTableRef');

  const handleSubmit = async () => {
    await formRef.value!.validate();
    currentTableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: currentTableRef.value!.getValue(),
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    currentTableRef.value!.reset();
  };
</script>

<style lang="less" scoped>
  .mongo-reduce-shard-page {
    padding-bottom: 20px;
  }
</style>
