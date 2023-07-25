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
      基础信息
    </div>
    <div class="table-box">
      <BasicInfoTable
        ref="tableRef"
        :table-data="tableData" />
    </div>
    <div
      class="main-title title-spot mb-18">
      执行模式<span class="required" />
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
                自动执行
              </div>
              <div class="sub-title">
                单据审批通过之后即可执行
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
                定时执行
              </div>
              <div class="sub-title">
                指定时间执行
              </div>
            </div>
          </div>
        </BkRadio>
      </div>
    </BkRadioGroup>
    <template v-if="executeMode === ExecuteModes.SCHEDULED_EXECUTION">
      <div
        class="main-title title-spot mb-11">
        指定执行时间<span class="required" />
      </div>
      <BkDatePicker
        v-model="specifyExecuteTime"
        style="width:360px;"
        type="datetime" />
    </template>

    <div
      class="main-title title-spot mb-11">
      全局超时时间<span class="required" />
    </div>
    <div class="overtime-box">
      <BkInput
        v-model="overtime"
        clearable
        :min="0"
        style="width:150px;"
        type="number" />
      <span style="margin-left: 8px;">h</span>
    </div>

    <div
      class="main-title title-spot mb-15">
      修复数据<span class="required" />
    </div>
    <BkSwitcher
      v-model="isRepairData"
      style="width: 28px;"
      theme="primary" />
    <div
      class="main-title title-spot mb-18">
      修复模式<span class="required" />
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
                人工确认
              </div>
              <div class="sub-title">
                校验检查完成后，需人工确认后，方可执行修复动作
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
                自动修复
              </div>
              <div class="sub-title">
                校验检查完成后，将自动修复数据
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
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import BasicInfoTable from './basic-info-table/Index.vue';
  import  {
    type IDataRow,
    type TableRealRowData,
  } from './basic-info-table/Row.vue';

  interface InfoItem {
    bill_id: number; // 关联的(数据复制)单据ID
    src_cluster: string; // 源集群,来自于数据复制记录
    src_instances: string[]; // 源实例列表
    dst_cluster: string; // 目的集群,来自于数据复制记录
    key_white_regex: string;// 包含key
    key_black_regex:string;// 排除key
  }

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
      execute_mode: ExecuteModes,
      specified_execution_time: string,
      global_timeout: string,
      data_repair_enabled: boolean,
      repair_mode: RepairModes,
    }
  }

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const executeMode = ref(ExecuteModes.SCHEDULED_EXECUTION);
  const specifyExecuteTime = ref(new Date());
  const overtime = ref(0);
  const isRepairData = ref(true);
  const repairMode = ref(RepairModes.AUTO_REPAIR);
  const isSubmitting = ref(false);
  const tableData = shallowRef<IDataRow[]>([
    {
      billId: 0,
      relateTicket: 100,
      srcCluster: 'cache.online.dba.db',
      instances: t('全部'),
      targetCluster: 'dilhcoahco24sdmpdv',
      includeKey: ['*'],
      excludeKey: ['123\n666'],
    },
  ]);

  const rawTableData = [...toRaw(tableData.value)];
  const tableRef = ref();

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = async () => {
    const moreDataList = await tableRef.value.getValue() as TableRealRowData[];
    const infos = tableData.value.reduce((result: InfoItem[], item, index) => {
      const obj = {
        bill_id: item.billId,
        src_cluster: item.srcCluster,
        src_instances: moreDataList[index].instances,
        dst_cluster: item.targetCluster,
        key_white_regex: moreDataList[index].includeKey.join('\n'),
        key_black_regex: moreDataList[index].excludeKey.join('\n'),
      };
      result.push(obj);
      return result;
    }, []);
    return infos;
  };

  // 提交
  const handleSubmit = async () => {
    const infos = await generateRequestParam();
    const params: SubmitType = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATACOPY_CHECK_REPAIR,
      details: {
        execute_mode: executeMode.value,
        specified_execution_time: executeMode.value === ExecuteModes.SCHEDULED_EXECUTION ? dayjs(specifyExecuteTime.value).format('YYYY-MM-DD HH:mm:ss') : '',
        global_timeout: `${overtime.value}h`,
        data_repair_enabled: isRepairData.value,
        repair_mode: repairMode.value,
        infos,
      },
    };
    console.log('params: ', params);
    InfoBox({
      title: t('确认提交n个数据校验修复任务？', { n: tableData.value.length }),
      subTitle: t('请谨慎操作！'),
      width: 480,
      infoType: 'warning',
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
    tableData.value.length = 0;
    setTimeout(() => tableData.value = rawTableData);
    window.changeConfirm = false;
  };

</script>

<style lang="less" scoped>
.redis-page {
  display: flex;
  padding: 24px;
  margin: 20px 24px;
  overflow: hidden;
  background-color: #fff;
  flex-direction: column;

  .main-title {
    margin-top: 24px;
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
