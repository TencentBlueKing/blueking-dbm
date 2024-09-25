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
        :title="t('数据迁移：数据同步复制到新集群，迁移后将会对原库进行')" />
      <BkForm
        class="mt-24"
        form-type="vertical">
        <BkFormItem
          :label="t('迁移类型')"
          required>
          <BkRadioGroup v-model="ticketType">
            <BkRadioButton
              :label="TicketTypes.SQLSERVER_FULL_MIGRATE"
              style="width: 200px">
              {{ t('一次性全备迁移') }}
            </BkRadioButton>
            <BkRadioButton
              :label="TicketTypes.SQLSERVER_INCR_MIGRATE"
              style="width: 200px">
              {{ t('持续增量迁移') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <RenderData @batch-select-cluster="handleShowBatchSelector">
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :removeable="tableData.length < 2"
            @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
            @remove="handleRemove(index)" />
        </RenderData>
        <BkFormItem
          class="mt-24"
          :label="t('DB名处理')">
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
  import { reactive, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import RenderData from './components/render-data/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/render-data/Row.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const { ticketType: urlTicketType } = route.query as {
    ticketType: TicketTypes.SQLSERVER_FULL_MIGRATE | TicketTypes.SQLSERVER_INCR_MIGRATE;
  };

  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);

  const formData = reactive({
    need_auto_rename: false,
  });

  const ticketType = ref<typeof urlTicketType>(
    [TicketTypes.SQLSERVER_FULL_MIGRATE, TicketTypes.SQLSERVER_INCR_MIGRATE].includes(urlTicketType)
      ? urlTicketType
      : TicketTypes.SQLSERVER_FULL_MIGRATE,
  );
  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: (SqlServerSingleModel | SqlServerHaModel)[] }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcClusterData && !firstRow.dstClusterData;
  };

  useTicketCloneInfo({
    type: ticketType.value,
    onSuccess(cloneData) {
      tableData.value = cloneData.map((item) =>
        createRowData({
          srcClusterData: {
            id: item.src_cluster.id,
            domain: item.src_cluster.immute_domain,
            cloudId: item.src_cluster.bk_cloud_id,
            majorVersion: item.src_cluster.major_version,
          },
          dstClusterData: {
            id: item.dst_cluster.id,
            domain: item.dst_cluster.immute_domain,
            cloudId: item.dst_cluster.bk_cloud_id,
          },
          dbList: item.db_list,
          ignoreDbList: item.ignore_db_list,
          renameInfos: [],
        }),
      );
    },
  });

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: UnwrapRef<typeof selectedClusters>) => {
    selectedClusters.value = selected;
    const list = _.flatten(Object.values(selected));
    const newList = list.reduce((result, item) => {
      const row = createRowData({
        srcClusterData: {
          id: item.id,
          domain: item.master_domain,
          cloudId: item.bk_cloud_id,
          majorVersion: item.major_version,
        },
      });
      result.push(row);
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
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value!.map((item) => item.getValue()))
      .then((data) =>
        createTicket({
          ticket_type: ticketType.value,
          remark: '',
          details: {
            ...formData,
            infos: data,
          },
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
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
