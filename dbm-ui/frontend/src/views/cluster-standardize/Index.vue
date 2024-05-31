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
    <div class="cluster-standardize-view">
      <BkTab
        v-model:active="currentClusterType"
        class="top-tabs"
        type="unborder-card">
        <BkTabPanel
          v-for="item of panels"
          :key="item.name"
          :label="item.label"
          :name="item.name" />
      </BkTab>
      <div class="cluster-standardize-content">
        <BkAlert
          closable
          theme="info"
          :title="t('标准化部署管理集群所必须的 DB 工具，例如 mysql-crond、监控程序、备份工具等')" />
        <RenderData
          class="mt-20"
          @batch-select-cluster="handleShowBatchSelector">
          <RenderRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :inputed="inputedDomains"
            :removeable="tableData.length < 2"
            @add="() => handleAppend(index)"
            @input-cluster-finish="(data: TendbhaModel) => handleChangeCluster(index, data)"
            @remove="() => handleRemove(index)" />
        </RenderData>
      </div>
    </div>
    <template #action>
      <BkButton
        class="ml-20 w-88"
        :disabled="totalNum === 0"
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :selected="checkedMap"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from './components/cluster-selector/Index.vue';
  import RenderData from './components/render-table/RenderData.vue';
  import RenderRow, { createRowData, type IDataRow } from './components/render-table/RenderRow.vue';

  enum ClusterStandardTypes {
    MYSQL = 'tendbha',
    TENDIS_CACHE = 'tendis_cache',
    TENDIS_PLUS = 'tendis_plus',
    ES = 'es',
    KAFKA = 'kafka',
    HDFS = 'hdfs',
    PULSAR = 'pulsar',
    INFLUXDB = 'influx_db',
    SPIDER = 'spider',
  }

  const { t } = useI18n();

  const currentClusterType = ref<string>(ClusterStandardTypes.MYSQL);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<IDataRow[]>([createRowData()]);
  // 集群域名是否已存在表格的映射表
  const checkedMap = shallowRef<Record<string, TendbhaModel>>({});
  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.clusterType)).length);
  const inputedDomains = computed(() =>
    tableData.value.filter((item) => Boolean(item.domain)).map((item) => item.domain),
  );

  const panels = [
    { name: ClusterStandardTypes.MYSQL, label: 'MySQL', model: ClusterTypes.TENDBHA },
    // { name: ClusterStandardTypes.TENDIS_CACHE, label: 'TendisCache' },
    // { name: ClusterStandardTypes.TENDIS_PLUS, label: 'TendisPlus' },
    // { name: ClusterStandardTypes.ES, label: 'ES' },
    // { name: ClusterStandardTypes.KAFKA, label: 'Kafka' },
    // { name: ClusterStandardTypes.HDFS, label: 'HDFS' },
    // { name: ClusterStandardTypes.PULSAR, label: 'Pulsar' },
    // { name: ClusterStandardTypes.INFLUXDB, label: 'InfluxDB' },
    // { name: ClusterStandardTypes.SPIDER, label: 'Spider' },
  ];

  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 追加集群
  const handleAppend = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, createRowData());
    tableData.value = dataList;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.domain;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (data: TendbhaModel): IDataRow => ({
    rowKey: data.master_domain,
    id: data.id,
    domain: data.master_domain,
    clusterName: data.cluster_name,
    clusterType: data.cluster_type,
    bkBizId: data.bk_biz_id,
    bkBizName: data.bk_biz_name,
    status: data.status,
  });

  // 从集群选择器选择确认后
  const handelClusterChange = (selected: TendbhaModel[]) => {
    const newList = selected.reduce((result, item) => {
      const domain = item.master_domain;
      if (!checkedMap.value[domain]) {
        const row = generateRowDateFromRequest(item);
        result.push(row);
        checkedMap.value[domain] = item;
      }
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 表格访问入口单元格输入后
  const handleChangeCluster = (index: number, data: TendbhaModel) => {
    const isExist = inputedDomains.value.includes(data.master_domain);
    if (isExist) {
      return;
    }
    tableData.value[index] = generateRowDateFromRequest(data);
    checkedMap.value[data.master_domain] = data;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const domain = dataList[index]?.domain;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain) {
      const lastCheckMap = { ...checkedMap.value };
      delete lastCheckMap[domain];
      checkedMap.value = lastCheckMap;
    }
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    InfoBox({
      title: t('确认提交', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
      },
    });
  };

  // 点击重置按钮
  const handleReset = () => {
    tableData.value = [createRowData()];
    checkedMap.value = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .cluster-standardize-view {
    .top-tabs {
      padding: 0 24px;
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content {
        display: none;
      }
    }
  }

  .cluster-standardize-content {
    padding: 20px 24px;

    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
