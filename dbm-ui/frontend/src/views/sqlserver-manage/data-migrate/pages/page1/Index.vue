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
    <div class="sqlserver-manage-data-migrate-page">
      <BkAlert
        closable
        theme="info"
        :title="t('DB 重命名：database 重命名')" />
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <BkForm
        class="mt-24"
        form-type="vertical">
        <BkFormItem :label="t('迁移方式')">
          <BkRadioGroup v-model="formData.dts_mode">
            <BkRadio label="full">
              {{ t('完整备份迁移') }}
            </BkRadio>
            <BkRadio label="incr">
              {{ t('增量备份迁移') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem :label="t('DB名处理')">
          <BkRadioGroup v-model="formData.need_auto_rename">
            <BkRadio :label="false">
              {{ t('迁移后源DB继续使用，DB名不变') }}
            </BkRadio>
            <BkRadio label>
              {{ t('迁移后源DB不再使用，自动重命名') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
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
  <ClusterSelector
    v-model:is-show="isShowBatchSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :selected="selectedClusters"
    @change="handelClusterChange" />
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SqlServerHaClusterModel from '@services/model/sqlserver/sqlserver-ha-cluster';
  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import RenderData from './components/render-data/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/render-data/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);

  const formData = reactive({
    dts_mode: 'full',
    need_auto_rename: false,
  });

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: (SqlServerSingleClusterModel | SqlServerHaClusterModel)[] }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcClusterData && !firstRow.dstClusterData && !firstRow.dbList;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: {
    [key: string]: Array<SqlServerSingleClusterModel | SqlServerHaClusterModel>;
  }) => {
    selectedClusters.value = selected;
    const list = _.flatten(Object.values(selected));
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = createRowData({
          srcClusterData: {
            id: item.id,
            domain: item.master_domain,
            cloudId: item.bk_cloud_id,
            majorVersion: item.major_version,
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
    window.changeConfirm = true;
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
    const domain = dataList[index].srcClusterData?.domain;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBCLUSTER];
      selectedClusters.value[ClusterTypes.TENDBCLUSTER] = clustersArr.filter((item) => item.master_domain !== domain);
    }
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value!.map((item) => item.getValue()))
      .then((data) =>
        createTicket({
          ticket_type: 'SQLSERVER_DATA_MIGRATE',
          remark: '',
          details: {
            ...formData,
            infos: data,
          },
          bk_biz_id: currentBizId,
        }),
      )
      .then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'sqlServerDataMigrate',
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
  .sqlserver-manage-data-migrate-page {
    padding-bottom: 20px;

    .bk-form-label {
      font-size: 12px;
      font-weight: bold;
    }
  }
</style>
