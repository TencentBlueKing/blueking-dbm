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
    <div class="spider-manage-capacity-change-page">
      <BkAlert
        closable
        theme="info"
        :title="t('集群容量变更：通过部署新集群来实现原集群的扩容或缩容（集群分片数不变）')" />
      <RenderData
        v-slot="slotProps"
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :is-fixed="slotProps.isOverflow"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <BkForm
        class="mt-24 form-block"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('数据校验')"
          property="need_checksum"
          required>
          <BkSwitcher
            v-model="formData.need_checksum"
            theme="primary" />
        </BkFormItem>
        <template v-if="formData.need_checksum">
          <BkFormItem
            :label="t('校验时间')"
            property="trigger_checksum_type"
            required>
            <BkRadioGroup v-model="formData.trigger_checksum_type">
              <BkRadio label="now">
                {{ t('立即执行') }}
              </BkRadio>
              <BkRadio label="timer">
                {{ t('定时执行') }}
              </BkRadio>
            </BkRadioGroup>
          </BkFormItem>
          <BkFormItem
            v-if="formData.trigger_checksum_type === 'timer'"
            :label="t('定时执行')"
            property="trigger_checksum_time"
            required>
            <BkDatePicker
              v-model="formData.trigger_checksum_time"
              style="width: 360px"
              type="datetime" />
          </BkFormItem>
        </template>
      </BkForm>
      <ClusterSelector
        v-model:is-show="isShowBatchSelector"
        :cluster-types="[ClusterTypes.TENDBCLUSTER]"
        :selected="selectedClusters"
        @change="handelClusterChange" />
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
  import { useRouter } from 'vue-router';

  import SpiderModel from '@services/model/spider/spider';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{[key: string]: Array<SpiderModel>}>({ [ClusterTypes.TENDBCLUSTER]: [] });

  const formData = reactive({
    need_checksum: false,
    trigger_checksum_type: 'timer',
    trigger_checksum_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
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

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: Record<string, Array<SpiderModel>>) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.TENDBCLUSTER];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = createRowData({
          clusterData: {
            id: item.id,
            domain: item.master_domain,
          },
        });
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
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
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBCLUSTER];
      selectedClusters.value[ClusterTypes.TENDBCLUSTER] = clustersArr.filter(item => item.master_domain !== domain);
    }
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then(data => createTicket({
        ticket_type: 'TENDBCLUSTER_NODE_REBALANCE',
        remark: '',
        details: {
          ...formData,
          infos: data,
        },
        bk_biz_id: currentBizId,
      }))
      .then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'spiderCapacityChange',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.TENDBCLUSTER] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>
<style lang="less">
  .spider-manage-capacity-change-page {
    padding-bottom: 20px;

    .form-block{
      .bk-form-label{
        font-size: 12px;
        font-weight: bold;
        color: #313238;
      }

      .repair-mode-block{
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

            .bk-radio-input {
              margin-top: 2px;
            }
          }
        }
      }
    }
  }
</style>
