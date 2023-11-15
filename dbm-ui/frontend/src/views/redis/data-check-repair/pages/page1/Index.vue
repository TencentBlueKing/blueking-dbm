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
  <div class="redis-page">
    <div class="title-spot mb-16">
      {{ $t('基础信息') }}
    </div>
    <div class="table-box">
      <BasicInfoTable
        ref="tableRef"
        :table-data="tableData" />
    </div>
    <div
      class="main-title title-spot mb-18">
      {{ $t('执行模式') }}<span class="required" />
    </div>
    <BkRadioGroup
      v-model="executeMode">
      <div class="radio-group">
        <BkRadio
          class="radio-item"
          :label="ExecuteModes.AUTO_EXECUTION">
          <div class="radio-item__content">
            <div class="img-box">
              <DbIcon type="auto" />
            </div>
            <div class="title-box">
              <div class="title">
                {{ $t('自动执行') }}
              </div>
              <div class="sub-title">
                {{ $t('单据审批通过之后即可执行') }}
              </div>
            </div>
          </div>
        </BkRadio>
        <BkRadio
          class="radio-item mt-20"
          :label="ExecuteModes.SCHEDULED_EXECUTION">
          <div class="radio-item__content">
            <div class="img-box">
              <DbIcon type="clock" />
            </div>
            <div class="title-box">
              <div class="title">
                {{ $t('定时执行') }}
              </div>
              <div class="sub-title">
                {{ $t('指定时间执行') }}
              </div>
            </div>
          </div>
        </BkRadio>
      </div>
    </BkRadioGroup>
    <template v-if="executeMode === ExecuteModes.SCHEDULED_EXECUTION">
      <div
        class="main-title title-spot mb-11">
        {{ $t('指定执行时间') }}<span class="required" />
      </div>
      <BkDatePicker
        v-model="specifyExecuteTime"
        class="date-picker"
        type="datetime" />
    </template>

    <div
      class="main-title title-spot mb-11">
      {{ $t('指定停止时间') }}<span class="required" />
    </div>
    <div class="overtime-box">
      <BkDatePicker
        v-model="specifyStopTime"
        class="date-picker"
        :disabled="isKeepCheckAndRepair"
        type="datetime" />
      <BkCheckbox v-model="isKeepCheckAndRepair">
        {{ $t('一直保持校验修复') }}
      </BkCheckbox>
    </div>

    <div
      class="main-title title-spot mb-15">
      {{ $t('修复数据') }}<span class="required" />
    </div>
    <BkSwitcher
      v-model="isRepairData"
      style="width: 28px;"
      theme="primary" />
    <div
      class="main-title title-spot mb-18">
      {{ $t('修复模式') }}<span class="required" />
    </div>

    <BkRadioGroup
      v-model="repairMode">
      <div class="radio-group">
        <BkRadio
          class="radio-item"
          :label="RepairModes.MANUAL_CONFIRM">
          <div class="radio-item__content">
            <div class="img-box">
              <DbIcon type="manual-2" />
            </div>
            <div class="title-box">
              <div class="title">
                {{ $t('人工确认') }}
              </div>
              <div class="sub-title">
                {{ $t('校验检查完成后，需人工确认后，方可执行修复动作') }}
              </div>
            </div>
          </div>
        </BkRadio>
        <BkRadio
          class="radio-item mt-20"
          :label="RepairModes.AUTO_REPAIR">
          <div class="radio-item__content">
            <div class="img-box">
              <DbIcon type="clock" />
            </div>
            <div class="title-box">
              <div class="title">
                {{ $t('自动修复') }}
              </div>
              <div class="sub-title">
                {{ $t('校验检查完成后，将自动修复数据') }}
              </div>
            </div>
          </div>
        </BkRadio>
      </div>
    </BkRadioGroup>
    <div class="btns">
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="$t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="$t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </dbpopconfirm>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisDSTHistoryJobModel from '@services/model/redis/redis-dst-history-job';
  import { createTicket } from '@services/source/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { LocalStorageKeys, TicketTypes  } from '@common/const';

  import { formatDatetime } from '@views/redis/common/utils';

  import BasicInfoTable from './basic-info-table/Index.vue';
  import  {
    type IDataRow,
    type InfoItem,
  } from './basic-info-table/Row.vue';


  enum ExecuteModes {
    AUTO_EXECUTION = 'auto_execution',
    SCHEDULED_EXECUTION = 'scheduled_execution'
  }

  enum RepairModes {
    AUTO_REPAIR = 'auto_repair',
    MANUAL_CONFIRM = 'manual_confirm'
  }

  type SubmitType = SubmitTicket<TicketTypes, InfoItem[]> & {
    details: {
      execute_mode: ExecuteModes, // 执行模式
      specified_execution_time: string, // 定时执行,指定执行时间
      check_stop_time: string, // 校验终止时间,
      keep_check_and_repair: boolean, // 是否一直保持校验
      data_repair_enabled: boolean, // 是否修复数据
      repair_mode: RepairModes,
    }
  }

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  // TODO:
  // 自动执行 时， 停止时间 不能小于 当前时间，后台会检查；
  // 定时执行时， 停止时间 不能小于 定时执行的时间，，后台会检查；
  const executeMode = ref(ExecuteModes.SCHEDULED_EXECUTION);
  const specifyExecuteTime = ref(new Date());
  const specifyStopTime = ref(new Date());
  const overtime = ref(0);
  const isRepairData = ref(true);
  const repairMode = ref(RepairModes.AUTO_REPAIR);
  const isSubmitting = ref(false);
  const tableData = shallowRef<IDataRow[]>([]);
  const tableRef = ref();
  const isKeepCheckAndRepair = ref(true);

  const recoverDataListFromLocalStorage = () => {
    const r = localStorage.getItem(LocalStorageKeys.REDIS_DATA_CHECK_AND_REPAIR);
    if (!r) {
      return;
    }
    const item = JSON.parse(r) as RedisDSTHistoryJobModel;
    tableData.value = [{
      billId: item.bill_id,
      srcCluster: item.src_cluster,
      targetCluster: item.dst_cluster,
      relateTicket: item.bill_id,
      instances: t('全部'),
      includeKey: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
      excludeKey: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
    }];
    setTimeout(() => {
      localStorage.removeItem(LocalStorageKeys.REDIS_DATA_CHECK_AND_REPAIR);
    });
  };
  recoverDataListFromLocalStorage();

  // 提交
  const handleSubmit = async () => {
    const infos = await tableRef.value.getValue() as InfoItem[];
    const params: SubmitType = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATACOPY_CHECK_REPAIR,
      details: {
        execute_mode: executeMode.value,
        specified_execution_time: executeMode.value === ExecuteModes.SCHEDULED_EXECUTION ? formatDatetime(specifyExecuteTime.value) : '',
        check_stop_time: isKeepCheckAndRepair.value ? '' : formatDatetime(specifyStopTime.value),
        keep_check_and_repair: isKeepCheckAndRepair.value,
        data_repair_enabled: isRepairData.value,
        repair_mode: repairMode.value,
        infos,
      },
    };
    InfoBox({
      title: t('确认提交数据校验修复任务？'),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisToolboxDataCheckRepair',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            console.error('submit data check repair ticket error', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    executeMode.value = ExecuteModes.SCHEDULED_EXECUTION;
    specifyExecuteTime.value = new Date();
    specifyStopTime.value = new Date();
    repairMode.value = RepairModes.AUTO_REPAIR;
    overtime.value = 0;
    tableData.value = [];
    setTimeout(() => {
      recoverDataListFromLocalStorage();
    });
    window.changeConfirm = false;
  };

</script>

<style lang="less" scoped>
.redis-page {
  display: flex;
  padding: 24px;
  margin-top: -4px;
  overflow: hidden;
  background-color: #fff;
  flex-direction: column;

  .main-title {
    margin-top: 24px;
  }

  .date-picker {
    width:360px;
    margin-right: 12px;
  }

  .overtime-box {
    display: flex;
    width: 100%;
    align-items: center;
  }

  .bk-radio-group {
    .radio-group {
      display: flex;
      flex-direction: column;

      .radio-item {
        margin: 0;
        align-items: flex-start;

        .radio-item__content {
          display: flex;
          margin-left: 5px;
          color: #63656E;

          .img-box {
            width: 18px;

            img {
              width: 18px;
              object-fit: contain;
            }
          }

          .title-box {
            display: flex;
            flex-direction: column;

            .title {
              margin-bottom: 4px;
              font-weight: 700;
              color: #63656E;
            }
          }
        }
      }
    }
  }

  .btns {
    display: flex;
    width: 100%;
    margin-top: 32px;
  }
}


</style>
