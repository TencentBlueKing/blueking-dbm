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
          :data="item"
          :inputed="inputedDomains"
          :removeable="tableData.length < 2"
          @add="() => handleAppend(index)"
          @input-cluster-finish="(data: ClusterModel) => inputClusterFinish(index, data)"
          @remove="() => handleRemove(index)" />
      </RenderData>
    </div>
    <template #action>
      <BkButton
        class="ml-24 w-88"
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
      :db-type="DBTypes.MYSQL"
      :selected="selected"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createTicket } from '@services/source/ticket';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type ICluster } from '../cluster-selector/Index.vue';
  import type { ClusterModel } from '../common/RenderCluster.vue';

  import RenderData from './components/render-data/Index.vue';
  import RenderRow, { createRowData, type IDataRow } from './components/render-data/Row.vue';

  const { t } = useI18n();
  const router = useRouter();

  // 集群域名是否已存在表格的映射表
  let domainMemo = {} as Record<string, boolean>;

  const isShowBatchSelector = ref(false);
  const tableData = ref<IDataRow[]>([createRowData()]);
  const selected = shallowRef<Record<string, ICluster[]>>({
    [ClusterTypes.TENDBHA]: [] as ICluster[],
    [ClusterTypes.TENDBSINGLE]: [] as ICluster[],
  });

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.clusterType)).length);
  const inputedDomains = computed(() =>
    tableData.value.filter((item) => Boolean(item.domain)).map((item) => item.domain),
  );

  const { run: createTicketRun, loading: isSubmitting } = useRequest(createTicket, {
    manual: true,
    onSuccess(data) {
      router.push({
        name: 'PlatformClusterStandardize',
        query: {
          ticketId: data.id,
        },
        params: {
          page: 'success',
        },
      });
    },
  });

  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.domain;
  };

  // 从集群选择器选择确认后
  const handelClusterChange = (data: Record<string, ICluster[]>) => {
    selected.value = data;
    const newList = Object.values(data)
      .flat()
      .reduce<IDataRow[]>((result, item) => {
        const domain = item.immute_domain;
        if (!domainMemo[domain]) {
          result.push(createRowData(item));
          domainMemo[domain] = true;
        }
        return result;
      }, []);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 表格访问入口单元格输入后
  const inputClusterFinish = (index: number, data: ClusterModel) => {
    tableData.value[index] = createRowData(data);
    selected.value[data.cluster_type].push({
      ...data,
      bk_cloud_name: '',
      db_module_name: '',
    });
  };

  // 追加集群
  const handleAppend = (index: number) => {
    tableData.value.splice(index + 1, 0, createRowData());
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const { domain, clusterType } = tableData.value[index];
    tableData.value.splice(index, 1);
    if (domain) {
      delete domainMemo[domain];
      if (selected.value[clusterType]) {
        selected.value[clusterType] = selected.value[clusterType].filter((item) => item.immute_domain !== domain);
      }
    }
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const clusters = Object.values(selected.value).flat();
    const ticketTypeMap = {
      [ClusterTypes.TENDBHA]: TicketTypes.MYSQL_HA_STANDARDIZE,
      [ClusterTypes.TENDBSINGLE]: TicketTypes.TENDBSINGLE_STANDARDIZE,
    };
    createTicketRun({
      ticket_type: ticketTypeMap[clusters[0].cluster_type as keyof typeof ticketTypeMap],
      bk_biz_id: clusters[0].bk_biz_id,
      remark: '',
      details: {
        infos: {
          cluster_ids: clusters.map((item) => item.id),
        },
      },
    });
  };

  // 点击重置按钮
  const handleReset = () => {
    tableData.value = [createRowData()];
    selected.value = {
      [ClusterTypes.TENDBHA]: [],
      [ClusterTypes.TENDBSINGLE]: [],
    };
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .cluster-standardize-content {
    padding: 20px 24px;

    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
