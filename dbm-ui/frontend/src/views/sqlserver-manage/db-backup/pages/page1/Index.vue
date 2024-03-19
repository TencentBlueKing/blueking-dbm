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
        :title="t('数据库备份：指定DB备份，支持模糊匹配')" />
      <!-- <BkButton
        class="mt16"
        @click="handleShowBatchEntry">
        <DbIcon
          class="mr8"
          type="add" />
        {{ t('批量录入') }}
      </BkButton> -->
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="() => handleAppend(index)"
          @input-backup-dbs-finish="(backupDbs: string[]) => handleDbListChange(index, backupDbs, 'backupDbs')"
          @input-cluster-finish="(domain: string) => handleClusterChange(index, domain)"
          @input-ignore-dbs-finish="(ignoreDbs: string[]) => handleDbListChange(index, ignoreDbs, 'ignoreDbs')"
          @remove="() => handleRemove(index)"
          @show-final-reviewer="() => handleShowFianlDbReviewer(item)" />
      </RenderData>
      <DbForm
        class="db-backup-form mt16"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('备份方式')"
          property="backup_type"
          required>
          <BkRadioGroup
            v-model="formData.backup_type"
            size="small">
            <BkRadio label="full_backup">
              {{ t('全量备份') }}
            </BkRadio>
            <BkRadio label="log_backup">
              {{ t('增量备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('备份位置')"
          property="backup_place"
          required>
          <BkSelect
            v-model="formData.backup_place"
            disabled
            :list="backupLocationList"
            style="width: 360px" />
        </BkFormItem>
        <BkFormItem
          :label="t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup
            v-model="formData.file_tag"
            size="small">
            <template v-if="isBackupTypeFull">
              <BkRadio label="LONGDAY_DBFILE_3Y"> 3 {{ t('年') }} </BkRadio>
              <BkRadio label="MSSQL_FULL_BACKUP"> 30 {{ t('天') }} </BkRadio>
            </template>
            <template v-else>
              <BkRadio
                disabled
                label="MSSQL_FULL_BACKUP">
                15 {{ t('天') }}
              </BkRadio>
            </template>
          </BkRadioGroup>
        </BkFormItem>
      </DbForm>
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
    <!-- <BatchEntry
      v-model:is-show="isShowBatchEntry"
      @change="handleBatchEntry" /> -->
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
    <DbSideslider
      v-if="currentRowData"
      v-model:is-show="isShowFianlDbReviewer"
      quick-close
      :width="960">
      <template #header>
        {{ t('预览DB结果列表') }}
        <BkTag class="ml-8">{{ currentRowData.domain }}</BkTag>
      </template>
      <FianlDbReviewer
        :data="currentRowData"
        @change="handleDbChage" />
    </DbSideslider>
  </SmartAction>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SqlServerHaClusterModel from '@services/model/sqlserver/sqlserver-ha-cluster';
  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';
  import { filterClusters } from '@services/source/dbbase';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector-new/Index.vue';

  // import BatchEntry, { type IValue as IBatchEntryValue } from './components/BatchEntry/Index.vue';
  import FianlDbReviewer from './components/FianlDbReviewer/Index.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderRow, { createRowData, type IDataRow } from './components/RenderData/RenderRow.vue';

  type SqlserverModel = SqlServerSingleClusterModel | SqlServerHaClusterModel;

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const backupLocationList = [
    {
      value: 'master',
      label: t('主库主机'),
    },
  ];

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_SINGLE]: {
      name: t('单节点集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      name: t('主从集群'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const createDefaultData = () => ({
    backup_type: 'full_backup',
    backup_place: 'master',
    file_tag: 'LONGDAY_DBFILE_3Y',
  });

  const rowRefs = ref<InstanceType<typeof RenderRow>[]>();
  const isShowBatchSelector = ref(false);
  // const isShowBatchEntry = ref(false);
  const isSubmitting = ref(false);
  const isShowFianlDbReviewer = ref(false);
  const currentRowData = ref<IDataRow>();
  const tableData = ref<IDataRow[]>([createRowData()]);
  const formData = reactive(createDefaultData());

  const selectedClusters = shallowRef<{ [key: string]: (SqlServerSingleClusterModel | SqlServerHaClusterModel)[] }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.domain)).length);
  const isBackupTypeFull = computed(() => formData.backup_type === 'full_backup');

  watch(
    () => formData.backup_type,
    () => {
      formData.file_tag = isBackupTypeFull.value ? 'LONGDAY_DBFILE_3Y' : 'MSSQL_FULL_BACKUP';
    },
  );

  // 显示批量录入
  // const handleShowBatchEntry = () => {
  //   isShowBatchEntry.value = true;
  // };

  // 批量录入
  // const handleBatchEntry = (list: Array<IBatchEntryValue>) => {
  //   const newList = list.map((item) => createRowData(item));
  //   if (checkListEmpty(tableData.value)) {
  //     tableData.value = newList;
  //   } else {
  //     tableData.value = [...tableData.value, ...newList];
  //   }
  //   window.changeConfirm = true;
  // };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.domain;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: { id: number; exact_domain: string; cluster_type: string }) => ({
    rowKey: item.exact_domain,
    isLoading: false,
    domain: item.exact_domain,
    clusterId: item.id,
    clusterType: item.cluster_type,
    backupDbs: [] as string[],
    ignoreDbs: [] as string[],
  });

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: SqlserverModel[] }) => {
    selectedClusters.value = selected;
    let list: SqlserverModel[] = [];

    if (selected[ClusterTypes.SQLSERVER_SINGLE]) {
      list = selected[ClusterTypes.SQLSERVER_SINGLE];
    }
    if (selected[ClusterTypes.SQLSERVER_HA]) {
      list = [...list, ...selected[ClusterTypes.SQLSERVER_HA]];
    }

    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        domainMemo[domain] = true;
        return [...result, generateRowDateFromRequest({...item, exact_domain: item.master_domain})];
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

  // 输入集群后查询集群信息并填充到table
  const handleClusterChange = async (index: number, domain: string) => {
    if (!domain) {
      const { domain } = tableData.value[index];
      domainMemo[domain] = false;
      tableData.value[index].domain = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await filterClusters({
      bk_biz_id: currentBizId,
      exact_domain: domain,
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });

    if (result.length < 1) {
      return;
    }
    const item = result[0];
    const row = generateRowDateFromRequest(item);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[item.cluster_type].push(item);
  };

  const handleDbListChange = (index: number, dbList: string[], fieldName: 'backupDbs' | 'ignoreDbs') => {
    Object.assign(tableData.value[index], { [fieldName]: dbList });
  };

  // 追加集群
  const handleAppend = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, createRowData());
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const { domain, clusterType } = dataList[index];
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[clusterType];
      selectedClusters.value[clusterType] = clustersArr.filter((item) => item.master_domain !== domain);
    }
  };

  const handleShowFianlDbReviewer = (item: IDataRow) => {
    currentRowData.value = item;
    isShowFianlDbReviewer.value = true;
  };

  const handleDbChage = (backupDbs: string[], ignoreDbs: string[]) => {
    Object.assign(currentRowData.value, {
      backupDbs,
      ignoreDbs,
    });
  };

  const handleSubmit = async () => {
    const infos = await Promise.all(rowRefs.value!.map((item: { getValue: () => Promise<{
      cluster_id: number;
      backup_dbs: string[]
    }> }) => item.getValue()));

    InfoBox({
      title: t('确认提交n个数据库备份任务', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.SQLSERVER_BACKUP_DBS,
          details: {
            ...formData,
            infos,
          },
        })
          .then((data) => {
            window.changeConfirm = false;
            router.push({
              name: 'SqlServerDbBackup',
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
      },
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultData());
    selectedClusters.value[ClusterTypes.SQLSERVER_HA] = [];
    selectedClusters.value[ClusterTypes.SQLSERVER_SINGLE] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .db-backup-page {
    padding-bottom: 20px;

    .db-backup-form {
      .bk-form-label {
        font-size: 12px;
      }
    }
  }
</style>
