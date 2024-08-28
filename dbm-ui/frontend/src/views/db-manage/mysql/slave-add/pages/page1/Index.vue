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
    <div class="mysql-slave-add-page">
      <BkAlert
        closable
        :title="t('添加从库_同机的所有集群会统一新增从库_但新机器不添加到域名解析中去')" />
      <BkButton
        class="slave-add-batch"
        @click="() => (isShowBatchInput = true)">
        <i class="db-icon-add" />
        {{ t('批量录入') }}
      </BkButton>
      <RenderData
        class="mb-20"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <BkForm form-type="vertical">
        <BkFormItem
          :label="t('备份源')"
          required>
          <BkRadioGroup v-model="backupSource">
            <BkRadio label="local">
              {{ t('本地备份') }}
            </BkRadio>
            <BkRadio label="remote">
              {{ t('远程备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
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
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getTendbhaList } from '@services/source/tendbha';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import BatchInput from './components/BatchInput.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_ADD_SLAVE,
    onSuccess(cloneData) {
      const { backupSource: sourceType, tableDataList } = cloneData;
      backupSource.value = sourceType;
      tableData.value = tableDataList;
      window.changeConfirm = true;
    },
  });

  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData()]);
  const backupSource = ref('local');
  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>();

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({ [ClusterTypes.TENDBHA]: [] });

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }

    const [firstRow] = list;
    return !firstRow.clusterData?.domain && !firstRow.newSlaveIp;
  };

  /**
   * 批量录入
   */
  const handleBatchInput = async (list: Array<{ cluster: string; ip: string }>) => {
    const domains = Array.from(new Set(list.map((item) => item.cluster)));
    const domainsInfoResults = await getTendbhaList({
      domain: domains.join(','),
      limit: -1,
    });

    const domainsInfoMap = domainsInfoResults.results.reduce<Record<string, TendbhaModel>>(
      (results, item) =>
        Object.assign(results, {
          [item.master_domain]: item,
        }),
      {},
    );
    const formatList = list.map((item) => ({
      ...createRowData(),
      clusterData: {
        id: domainsInfoMap[item.cluster].id,
        domain: item.cluster,
        cloudId: domainsInfoMap[item.cluster].bk_cloud_id,
      },
      newSlaveIp: item.ip,
    }));

    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  /**
   * 集群选择器批量选择
   */
  const handleBatchSelectorChange = (selected: Record<string, Array<TendbhaModel>>) => {
    selectedClusters.value = selected;
    const formatList = selected[ClusterTypes.TENDBHA].reduce<IDataRow[]>((results, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = {
          ...createRowData(),
          clusterData: {
            id: item.id,
            domain: item.master_domain,
            cloudId: item.bk_cloud_id,
          },
        };
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
  };

  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const domain = dataList[index].clusterData?.domain;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
      selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter((item) => item.master_domain !== domain);
    }
    tableData.value.splice(index, 1);
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, sourceData);
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value![rowRefs.value!.length - 1].getValue();
    });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value!.map((item) => item.getValue()))
      .then((data) => {
        const params = {
          ticket_type: TicketTypes.MYSQL_ADD_SLAVE,
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            infos: data,
            backup_source: backupSource.value,
          },
        };

        return createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLSlaveAdd',
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
  };
</script>

<style lang="less">
  .mysql-slave-add-page {
    padding-bottom: 20px;

    .bk-form-label {
      font-weight: bold;
      color: #313238;
      font-size: 12px;
    }

    .bk-radio-label {
      font-size: 12px;
    }

    .slave-add-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }
  }
</style>
