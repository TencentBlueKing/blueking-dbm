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
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="form"
      class="redis-datacopy-check-repair toolbox-form mt-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem :label="t('基础信息')">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <EditableColumn
              :label="t('关联单据')"
              :width="200">
              <EditableBlock style="color: #3a84ff">{{ item.bill_id }}</EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('源集群')"
              :width="300">
              <EditableBlock>{{ item.src_cluster }}</EditableBlock>
            </EditableColumn>
            <InstanceSelectColumn
              v-model="item.src_instances"
              :src-cluster="item.src_cluster" />
            <EditableColumn
              :label="t('目标集群')"
              :width="300">
              <EditableBlock>{{ item.dst_cluster }}</EditableBlock>
            </EditableColumn>
            <RegexKeysColumn
              v-model="item.key_white_regex"
              field="key_white_regex"
              :label="t('包含 Key')"
              @batch-edit="handleColumnBatchEdit">
            </RegexKeysColumn>
            <RegexKeysColumn
              v-model="item.key_black_regex"
              field="key_black_regex"
              :label="t('排除 Key')"
              @batch-edit="handleColumnBatchEdit">
            </RegexKeysColumn>
          </EditableRow>
        </EditableTable>
      </BkFormItem>
      <BkFormItem
        :label="t('执行模式')"
        property="execute_mode"
        required>
        <ModeRadio
          v-model="formData.execute_mode"
          :list="ExecuteModeList" />
      </BkFormItem>
      <BkFormItem
        v-if="formData.execute_mode === ExecuteModes.SCHEDULED_EXECUTION"
        :label="t('指定执行时间')"
        property="specified_execution_time"
        required>
        <BkDatePicker
          v-model="formData.specified_execution_time"
          class="date-picker"
          type="datetime" />
      </BkFormItem>
      <BkFormItem
        :label="t('指定停止时间')"
        property="check_stop_time"
        required>
        <BkDatePicker
          v-model="formData.check_stop_time"
          class="date-picker"
          :disabled="formData.keep_check_and_repair"
          type="datetime" />
        <BkCheckbox
          v-model="formData.keep_check_and_repair"
          class="ml-12">
          {{ t('一直保持校验修复') }}
        </BkCheckbox>
      </BkFormItem>
      <BkFormItem
        :label="t('修复数据')"
        property="data_repair_enabled"
        required>
        <BkSwitcher
          v-model="formData.data_repair_enabled"
          style="width: 28px"
          theme="primary" />
      </BkFormItem>
      <BkFormItem
        :label="t('修复数据')"
        property="repair_mode"
        required>
        <ModeRadio
          v-model="formData.repair_mode"
          :list="RepairModeList" />
      </BkFormItem>
      <TicketPayload v-model="formData" />
    </DbForm>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import RedisDSTHistoryJobModel from '@services/model/redis/redis-dst-history-job';
  import { type Redis } from '@services/model/ticket/ticket';
  import { ExecuteModes, RepairModes } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { LocalStorageKeys, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import RegexKeysColumn from '@views/db-manage/redis/common/toolbox-field/regex-keys-column/Index.vue';
  import { formatDatetime } from '@views/db-manage/redis/common/utils';

  import InstanceSelectColumn from './components/InstanceSelectColumn.vue';
  import ModeRadio from './components/ModeRadio.vue';

  interface IDataRow {
    bill_id: number; // 关联的(数据复制)单据ID
    src_cluster: string; // 源集群,来自于数据复制记录
    src_instances: string[]; // 源实例列表
    dst_cluster: string; // 目的集群,来自于数据复制记录
    key_white_regex: string[]; // 包含key
    key_black_regex: string[]; // 排除key
  }

  // TODO:
  // 自动执行 时， 停止时间 不能小于 当前时间，后台会检查；
  // 定时执行 时， 停止时间 不能小于 定时执行的时间，后台会检查；
  const createDefaultFormData = () => ({
    tableData: [] as IDataRow[],
    execute_mode: ExecuteModes.SCHEDULED_EXECUTION,
    specified_execution_time: new Date(),
    check_stop_time: new Date(),
    keep_check_and_repair: true,
    data_repair_enabled: true,
    repair_mode: RepairModes.AUTO_REPAIR,
    ...createTickePayload(),
  });

  const { t } = useI18n();

  // 单据克隆
  useTicketDetail<Redis.DatacopyCheckRepair>(TicketTypes.REDIS_DATACOPY_CHECK_REPAIR, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos } = details;
      const info = infos[0];
      Object.assign(formData, {
        tableData: [
          {
            ...infos[0],
            key_white_regex: info.key_white_regex === '' ? [] : info.key_white_regex.split('\n'),
            key_black_regex: info.key_black_regex === '' ? [] : info.key_black_regex.split('\n'),
          },
        ],
        execute_mode: details.execute_mode,
        specified_execution_time: dayjs(details.specified_execution_time).toDate(),
        check_stop_time: dayjs(details.check_stop_time).toDate(),
        keep_check_and_repair: details.keep_check_and_repair,
        data_repair_enabled: details.data_repair_enabled,
        repair_mode: details.repair_mode,
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    execute_mode: string;
    specified_execution_time: string; // 定时执行,指定执行时间
    check_stop_time: string; // 校验终止时间,
    keep_check_and_repair: boolean; // 是否一直保持校验
    data_repair_enabled: boolean; // 是否修复数据
    repair_mode: string;
    infos: [
      {
        bill_id: number; // 关联的(数据复制)单据ID
        src_cluster: string; // 源集群,来自于数据复制记录
        src_instances: string[]; // 源实例列表
        dst_cluster: string; // 目的集群,来自于数据复制记录
        key_white_regex: string; // 包含key
        key_black_regex: string; // 排除key
      },
    ];
  }>(TicketTypes.REDIS_DATACOPY_CHECK_REPAIR);

  const editableTableRef = useTemplateRef('editableTable');

  const ExecuteModeList = [
    {
      label: ExecuteModes.AUTO_EXECUTION,
      icon: 'auto',
      title: t('自动执行'),
      subTitle: t('单据审批通过之后即可执行'),
    },
    {
      label: ExecuteModes.SCHEDULED_EXECUTION,
      icon: 'clock',
      title: t('定时执行'),
      subTitle: t('指定时间执行'),
    },
  ];

  const RepairModeList = [
    {
      label: RepairModes.MANUAL_CONFIRM,
      icon: 'manual-2',
      title: t('人工确认'),
      subTitle: t('校验检查完成后，需人工确认后，方可执行修复动作'),
    },
    {
      label: RepairModes.AUTO_REPAIR,
      icon: 'clock',
      title: t('自动修复'),
      subTitle: t('校验检查完成后，将自动修复数据'),
    },
  ];

  const formData = reactive(createDefaultFormData());

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const recoverDataListFromLocalStorage = () => {
    const storageItem = localStorage.getItem(LocalStorageKeys.REDIS_DATA_CHECK_AND_REPAIR);
    if (!storageItem) {
      return;
    }
    const item = JSON.parse(storageItem) as RedisDSTHistoryJobModel;
    formData.tableData = [
      {
        bill_id: item.bill_id,
        src_cluster: item.src_cluster,
        src_instances: [],
        dst_cluster: item.dst_cluster,
        key_white_regex: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
        key_black_regex: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
      },
    ];
    setTimeout(() => {
      localStorage.removeItem(LocalStorageKeys.REDIS_DATA_CHECK_AND_REPAIR);
    });
  };
  recoverDataListFromLocalStorage();

  const handleColumnBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      const info = formData.tableData[0];
      createTicketRun({
        details: {
          execute_mode: formData.execute_mode,
          specified_execution_time:
            formData.execute_mode === ExecuteModes.SCHEDULED_EXECUTION
              ? formatDatetime(formData.specified_execution_time)
              : '',
          check_stop_time: formData.keep_check_and_repair ? '' : formatDatetime(formData.check_stop_time),
          keep_check_and_repair: formData.keep_check_and_repair,
          data_repair_enabled: formData.data_repair_enabled,
          repair_mode: formData.repair_mode,
          infos: [
            {
              ...info,
              key_white_regex: info.key_white_regex.join('\n'),
              key_black_regex: info.key_black_regex.join('\n'),
            },
          ],
        },
        remark: formData.remark,
      });
    }
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .redis-datacopy-check-repair {
    padding: 24px;
    overflow: hidden;
    background-color: #fff;
  }
</style>
