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
    <div class="proxy-scale-down-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t(
            '数据复制：通过DTS能力，将原集群全部或者部分数据复制到目标集群，原集群和目标集群都可以为自建集群或者DBM托管集群',
          )
        " />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <BkFormItem
          :label="t('复制类型')"
          property="dts_copy_type"
          required>
          <BkRadioGroup v-model="formData.dts_copy_type">
            <BkRadioButton
              v-for="item in copyTypeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem>
          <Component
            :is="currentTable"
            ref="currentTableRef" />
        </BkFormItem>
        <BkFormItem
          :label="t('写入类型')"
          property="write_mode"
          required>
          <BkRadioGroup v-model="formData.write_mode">
            <BkRadio
              v-for="item in writeTypeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('断开设置')"
          property="sync_disconnect_type"
          required>
          <BkRadioGroup v-model="formData.sync_disconnect_type">
            <BkRadio
              v-for="item in disconnectTypeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <template v-if="formData.sync_disconnect_type !== DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION">
          <BkFormItem
            :label="t('提醒频率')"
            property="sync_disconnect_reminder_frequency"
            required>
            <BkRadioGroup v-model="formData.sync_disconnect_reminder_frequency">
              <BkRadio
                v-for="item in remindFrequencyTypeList"
                :key="item.value"
                :label="item.value">
                {{ item.label }}
              </BkRadio>
            </BkRadioGroup>
          </BkFormItem>
          <BkFormItem
            :label="t('校验与修复类型')"
            property="data_check_repair_type"
            required>
            <BkRadioGroup v-model="formData.data_check_repair_type">
              <BkRadio
                v-for="item in repairAndVerifyTypeList"
                :key="item.value"
                :label="item.value">
                {{ item.label }}
              </BkRadio>
            </BkRadioGroup>
          </BkFormItem>
          <BkFormItem
            v-if="formData.data_check_repair_type !== RepairAndVerifyModes.NO_CHECK_NO_REPAIR"
            :label="t('校验与修复频率设置')"
            property="data_check_repair_execution_frequency"
            required>
            <BkSelect
              v-model="formData.data_check_repair_execution_frequency"
              class="select-box">
              <BkOption
                v-for="(item, index) in repairAndVerifyFrequencyList"
                :key="index"
                :label="item.label"
                :value="item.value" />
            </BkSelect>
          </BkFormItem>
        </template>
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
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="w-88 ml-8"
          :disabled="isSubmitting"
          style="margin-left: 8px">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import {
    CopyModes,
    DisconnectModes,
    RemindFrequencyModes,
    RepairAndVerifyFrequencyModes,
    RepairAndVerifyModes,
    WriteModes,
  } from '@services/model/redis/redis-dst-history-job';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisDTSHistoryJobs } from '@services/source/redisDts';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import {
    copyTypeList,
    disconnectTypeList,
    remindFrequencyTypeList,
    repairAndVerifyFrequencyList,
    repairAndVerifyTypeList,
    writeTypeList,
  } from '@views/db-manage/redis/common/const';

  import RenderCrossBusinessTable from './components/cross-business/Index.vue';
  import RenderIntraBusinessToThirdPartTable from './components/intra-business-third/Index.vue';
  import RenderSelfbuiltToIntraBusinessTable from './components/selfbuilt-clusters-intra-business/Index.vue';
  import RenderWithinBusinessTable from './components/within-business/Index.vue';

  type CurrntTableRef =
    | InstanceType<typeof RenderCrossBusinessTable>
    | InstanceType<typeof RenderIntraBusinessToThirdPartTable>
    | InstanceType<typeof RenderSelfbuiltToIntraBusinessTable>
    | InstanceType<typeof RenderWithinBusinessTable>;

  const createDefaultFormData = () => ({
    data_check_repair_execution_frequency: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
    data_check_repair_type: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
    dts_copy_type: CopyModes.INTRA_BISNESS,
    payload: createTickePayload(),
    sync_disconnect_reminder_frequency: RemindFrequencyModes.ONCE_DAILY,
    sync_disconnect_type: DisconnectModes.KEEP_SYNC_WITH_REMINDER,
    write_mode: WriteModes.DELETE_AND_WRITE_TO_REDIS,
  });

  const { t } = useI18n();
  const route = useRoute();

  useTicketDetail<Redis.ClusterDataCopy>(TicketTypes.REDIS_CLUSTER_DATA_COPY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        data_check_repair_execution_frequency: details.data_check_repair_setting.execution_frequency,
        data_check_repair_type: details.data_check_repair_setting.type,
        dts_copy_type: details.dts_copy_type,
        payload: createTickePayload(ticketDetail),
        sync_disconnect_reminder_frequency: details.sync_disconnect_setting.reminder_frequency,
        sync_disconnect_type: details.sync_disconnect_setting.type,
        write_mode: details.write_mode,
      });

      nextTick(() => {
        currentTableRef.value!.setTableByTicketClone(ticketDetail);
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    data_check_repair_setting: {
      execution_frequency: string;
      type: string;
    };
    dts_copy_type: string;
    infos: {
      dst_bk_biz_id?: number; // 跨业务
      dst_cluster: string | number;
      dst_cluster_password?: string; // 业务内至第三方
      key_black_regex: string;
      key_white_regex: string;
      src_cluster: string | number;
      src_cluster_password?: string; // 自建集群至业务内
      src_cluster_type?: string; // 自建集群至业务内
    }[];
    sync_disconnect_setting: {
      reminder_frequency: string;
      type: string;
    };
    write_mode: string;
  }>(TicketTypes.REDIS_CLUSTER_DATA_COPY);

  const formRef = useTemplateRef('form');

  const formData = reactive(createDefaultFormData());

  const currentTableRef = ref<CurrntTableRef>();

  const currentTable = computed(() => {
    const comMap = {
      [CopyModes.CROSS_BISNESS]: RenderCrossBusinessTable,
      [CopyModes.INTRA_BISNESS]: RenderWithinBusinessTable,
      [CopyModes.INTRA_TO_THIRD]: RenderIntraBusinessToThirdPartTable,
      [CopyModes.SELFBUILT_TO_INTRA]: RenderSelfbuiltToIntraBusinessTable,
    };
    return formData.dts_copy_type in comMap
      ? comMap[formData.dts_copy_type as keyof typeof comMap]
      : RenderSelfbuiltToIntraBusinessTable;
  });

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const infos = await currentTableRef.value!.getValue();
    if (infos.length > 0) {
      const isAutoDisconnect = formData.sync_disconnect_type === DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION;
      const details = {
        data_check_repair_setting: {
          execution_frequency:
            isAutoDisconnect || formData.data_check_repair_type === RepairAndVerifyModes.NO_CHECK_NO_REPAIR
              ? ''
              : formData.data_check_repair_execution_frequency,
          type: isAutoDisconnect ? '' : formData.data_check_repair_type,
        },
        dts_copy_type: formData.dts_copy_type,
        infos,
        sync_disconnect_setting: {
          reminder_frequency: isAutoDisconnect ? '' : formData.sync_disconnect_reminder_frequency,
          type: formData.sync_disconnect_type,
        },
        write_mode: formData.write_mode,
      };
      createTicketRun({
        details,
        ...formData.payload,
      });
    }
  };

  const handleReset = async () => {
    Object.assign(formData, createDefaultFormData());
    currentTableRef.value!.resetTable();
    window.changeConfirm = false;
  };

  onMounted(() => {
    const { historyJobId } = route.query;
    if (!historyJobId) {
      return;
    }
    getRedisDTSHistoryJobs({
      id: Number(historyJobId),
    }).then((result) => {
      if (result.jobs.length > 0) {
        const item = result.jobs[0];
        formData.dts_copy_type = item.dts_copy_type;
        formData.write_mode = item.write_mode;
        formData.sync_disconnect_type = item.sync_disconnect_type;
        formData.sync_disconnect_reminder_frequency = item.sync_disconnect_reminder_frequency;
        formData.data_check_repair_type = item.data_check_repair_type;
        formData.data_check_repair_execution_frequency = item.data_check_repair_execution_frequency;
        // 设值
        nextTick(() => {
          currentTableRef.value!.setTableByLocalStorage(item);
        });
      }
    });
  });
</script>

<style lang="less" scoped>
  .proxy-scale-down-page {
    padding-bottom: 20px;

    :deep(.bk-radio-button) {
      width: 180px;
    }

    .select-box {
      width: 460px;
    }
  }
</style>
