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
    <div class="db-backup-page">
      <BkAlert
        theme="info"
        :title="t('全库备份：所有库表备份, 除 MySQL 系统库和 DBA 专用库外')" />
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
          @input-cluster-finish="(item: IDataRow) => handleInputCluster(index, item)"
          @remove="handleRemove(index)" />
      </RenderData>
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <BkFormItem
          :label="t('备份类型')"
          property="backup_type"
          required>
          <BkRadioGroup v-model="formData.backup_type">
            <BkRadio label="logical">
              {{ t('逻辑备份') }}
            </BkRadio>
            <BkRadio label="physical">
              {{ t('物理备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup v-model="formData.file_tag">
            <BkRadio label="MYSQL_FULL_BACKUP">
              {{ t('30天') }}
            </BkRadio>
            <BkRadio label="LONGDAY_DBFILE_3Y">
              {{ t('3年') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </DbForm>
      <ClusterSelector
        v-model:is-show="isShowBatchSelector"
        :tab-list="clusterSelectorTabList"
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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SpiderModel from '@services/model/spider/spider';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/ClusterSelector.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const createDefaultData = () => ({
    backup_type: 'logical',
    file_tag: 'MYSQL_FULL_BACKUP',
  });

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const clusterSelectorTabList = [ClusterTypes.TENDBHA];

  const formRef = ref();
  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const formData = reactive(createDefaultData());

  const tableData = ref<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: Array<SpiderModel> }>({ [ClusterTypes.TENDBHA]: [] });

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData && !firstRow.backupLocal;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: {
    [key: string]: Array<{
      id: number;
      master_domain: string;
    }>;
  }) => {
    const newList = selected[ClusterTypes.TENDBHA].map((clusterData) =>
      createRowData({
        clusterData: {
          id: clusterData.id,
          domain: clusterData.master_domain,
        },
      }),
    );

    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入一个集群
  const handleInputCluster = (index: number, item: IDataRow) => {
    tableData.value[index] = item;
  };

  // 追加集群
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

  const handleSubmit = () => {
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue())).then((data) => {
      isSubmitting.value = true;
      createTicket({
        bk_biz_id: currentBizId,
        ticket_type: 'MYSQL_HA_FULL_BACKUP',
        remark: '',
        details: {
          infos: {
            ...formData,
            clusters: data,
          },
        },
      })
        .then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLDBBackup',
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
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultData());
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .db-backup-page {
    padding-bottom: 20px;

    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
