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
    <div class="mysql-checksum-page">
      <BkAlert
        closable
        :title="t('数据校验修复_对集群的主库和从库进行数据一致性校验和修复_其中MyISAM引擎库表不会被校验和修复')" />
      <BkButton
        class="checksum-batch"
        @click="() => (isShowBatchInput = true)">
        <i class="db-icon-add" />
        {{ t('批量录入') }}
      </BkButton>
      <div class="checksum-main">
        <RenderData
          @batch-edit="handleBatchEditColumn"
          @batch-select-cluster="handleShowBatchSelector">
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :removeable="tableData.length < 2"
            @add="(payload) => handleAppend(index, payload)"
            @cluster-input-finish="(clusterId) => handleChangeCluster(index, clusterId)"
            @remove="handleRemove(index)" />
        </RenderData>
        <DbForm
          ref="checksumFormRef"
          class="checksum-form toolbox-form"
          form-type="vertical"
          :model="formdata">
          <BkFormItem
            :label="t('定时执行时间')"
            property="timing"
            required>
            <div class="time-box">
              <TimeZonePicker style="width: 350px" />
              <BkDatePicker
                v-model="formdata.timing"
                class="ml-8"
                :disabled-date="disabledDate"
                :placeholder="t('请选择xx', [t('定时执行时间')])"
                style="width: 360px"
                type="datetime" />
            </div>
          </BkFormItem>
          <BkFormItem
            :label="t('全局超时时间')"
            property="runtime_hour"
            required>
            <BkInput
              v-model="formdata.runtime_hour"
              :max="168"
              :min="24"
              style="width: 200px"
              type="number" />
          </BkFormItem>
          <BkFormItem
            :label="t('数据修复')"
            required>
            <BkSwitcher
              v-model="formdata.data_repair.is_repair"
              theme="primary" />
          </BkFormItem>
          <BkFormItem
            v-if="formdata.data_repair.is_repair"
            :label="t('修复模式')"
            required>
            <BkRadioGroup
              v-model="formdata.data_repair.mode"
              class="repair-mode">
              <div class="item-box">
                <BkRadio label="manual">
                  <div class="item-content">
                    <DbIcon
                      class="item-flag"
                      type="account" />
                    <div class="item-label">
                      {{ t('人工确认') }}
                    </div>
                    <div>{{ t('校验检查完成需人工确认后_方可执行修复动作') }}</div>
                  </div>
                </BkRadio>
              </div>
              <div class="item-box">
                <BkRadio label="auto">
                  <div class="item-content">
                    <DbIcon
                      class="item-flag"
                      type="timed-task" />
                    <div class="item-label">
                      {{ t('自动修复') }}
                    </div>
                    <div>{{ t('校验检查完成后_将自动修复数据') }}</div>
                  </div>
                </BkRadio>
              </div>
            </BkRadioGroup>
          </BkFormItem>
          <TicketRemark v-model="formdata.remark" />
        </DbForm>
      </div>
    </div>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
  <BatchInput
    v-model:is-show="isShowBatchInput"
    @change="handleBatchInput" />
  <ClusterSelector
    v-model:is-show="isShowBatchSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
    @change="handleBatchSelectorChange" />
</template>

<script setup lang="tsx">
  import { format } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getTendbhaList } from '@services/source/tendbha';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo, useTimeZoneFormat } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import BatchInput, { type InputItem } from './components/BatchInput.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createInstanceData,
    createRowData,
    type IDataRow,
    type IDataRowBatchKey,
  } from './components/RenderData/Row.vue';

  const disabledDate = (date: Date | number) => {
    const day = new Date();
    day.setDate(day.getDate() - 1);
    const dateTime = typeof date === 'number' ? date : date.getTime();
    return dateTime < day.getTime();
  };

  const getCurrentDate = () => {
    const today = new Date();
    today.setSeconds(0);
    return today;
  };

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const router = useRouter();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_CHECKSUM,
    onSuccess(cloneData) {
      (tableData.value = cloneData.tableDataList), (formdata.timing = cloneData.timing);
      formdata.runtime_hour = cloneData.runtime_hour;
      formdata.data_repair = cloneData.data_repair;
      formdata.remark = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const checksumFormRef = ref();
  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({ [ClusterTypes.TENDBHA]: [] });

  const formdata = reactive({
    timing: getCurrentDate(),
    runtime_hour: 48,
    data_repair: {
      is_repair: true,
      mode: 'manual',
    },
    remark: '',
  });

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }

    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<InputItem>) {
    const clusterInfoResults = await getTendbhaList({
      domain: list.map((item) => item.cluster).join(','),
      limit: -1,
    });
    const clusterInfoMap = clusterInfoResults.results.reduce<Record<string, TendbhaModel>>((results, item) => {
      Object.assign(results, {
        [item.master_domain]: item,
      });
      return results;
    }, {});
    const formatList = list.map((item) => {
      const domain = item.cluster;
      const currentCluster = clusterInfoMap[domain];
      const masterInfo = currentCluster.masters[0];
      return {
        ...createRowData(),
        clusterData: {
          id: currentCluster.id,
          domain,
        },
        master: masterInfo ? `${masterInfo.ip}:${masterInfo.port}` : '',
        slaves: item.slaves,
        masterInstance: masterInfo || createInstanceData(),
        slaveList: currentCluster.slaves || [],
        dbPatterns: item.dbs,
        ignoreDbs: item.ignoreDbs,
        tablePatterns: item.tables,
        ignoreTables: item.ignoreTables,
      };
    });

    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  }

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  const generateRowDateFromRequest = (item: TendbhaModel) => {
    const domain = item.master_domain;
    const masterInfo = item.masters[0];

    return {
      ...createRowData(),
      clusterData: {
        id: item.id,
        domain,
      },
      master: masterInfo ? `${masterInfo.ip}:${masterInfo.port}` : '',
      masterInstance: masterInfo || createInstanceData(),
      slaveList: item.slaves || [],
    };
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, clusterId: number) => {
    if (tableData.value[index].clusterData?.id === clusterId) {
      return;
    }
    tableData.value[index].isLoading = true;
    const clusterInfoResults = await getTendbhaList({
      cluster_ids: clusterId,
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    const clusterInfo = clusterInfoResults.results[0];
    const row = generateRowDateFromRequest(clusterInfo);
    tableData.value[index] = row;
    domainMemo[clusterInfo.master_domain] = true;
    selectedClusters.value[ClusterTypes.TENDBHA].push(clusterInfo);
  };

  /**
   * 集群选择器批量选择
   */
  function handleBatchSelectorChange(selected: Record<string, Array<TendbhaModel>>) {
    selectedClusters.value = selected;
    const formatList = selected[ClusterTypes.TENDBHA].reduce<IDataRow[]>((results, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
        results.push(row);
        domainMemo[domain] = true;
      }
      return results;
    }, []);

    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  }

  const handleBatchEditColumn = (value: string | string[], filed: IDataRowBatchKey) => {
    if (!value || checkListEmpty(tableData.value)) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, {
        [filed]: value,
      });
    });
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const domain = dataList[index].clusterData?.domain;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
      selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter((item) => item.master_domain !== domain);
    }
  };

  function handleReset() {
    tableData.value = [createRowData()];
    formdata.data_repair.is_repair = true;
    formdata.timing = getCurrentDate();
    formdata.runtime_hour = 48;
    formdata.remark = '';
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    domainMemo = {};
    window.changeConfirm = false;
  }

  function handleSubmit() {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) => {
        const params = {
          ticket_type: TicketTypes.MYSQL_CHECKSUM,
          bk_biz_id: globalBizsStore.currentBizId,
          remark: formdata.remark,
          details: {
            ...formdata,
            timing: formatDateToUTC(format(new Date(formdata.timing), 'yyyy-MM-dd HH:mm:ss')),
            infos: data,
          },
        };
        return createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'spiderChecksum',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        });
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  }
</script>

<style lang="less">
  .mysql-checksum-page {
    .checksum-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }

    .checksum-form {
      width: 100%;
      margin-top: 24px;
      margin-bottom: 32px;

      :deep(.bk-form-label) {
        font-weight: bold;
        color: @title-color;

        &::after {
          line-height: unset;
        }
      }

      .time-box {
        display: flex;
        align-items: center;
      }
    }

    .repair-mode {
      flex-direction: column;

      .item-box {
        & ~ .item-box {
          margin-top: 20px;
        }

        .item-content {
          position: relative;
          padding-left: 25px;
          font-size: 12px;
          line-height: 20px;
          color: #63656e;
        }

        .item-flag {
          position: absolute;
          left: 3px;
          font-size: 18px;
          color: #979ba5;
        }

        .item-label {
          font-weight: bold;
        }

        .bk-radio {
          align-items: flex-start;

          :deep(.bk-radio-input) {
            margin-top: 2px;
          }
        }
      }
    }
  }
</style>
