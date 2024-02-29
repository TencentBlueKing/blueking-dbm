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
  <SuccessView
    v-if="ticketId"
    :steps="[
      {
        title: $t('单据审批'),
        status: 'loading',
      },
      {
        title: $t('DB重命名_执行'),
      },
    ]"
    :ticket-id="ticketId"
    :title="$t('DB重命名任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="db-rename">
    <BkAlert
      closable
      :title="$t('DB重命名_database重命名')" />
    <div class="db-rename-operations">
      <BkButton
        class="db-rename-batch"
        @click="() => (isShowBatchInput = true)">
        <DbIcon type="add" />
        {{ $t('批量录入') }}
      </BkButton>
    </div>
    <ToolboxTable
      ref="toolboxTableRef"
      class="mb-20"
      :columns="columns"
      :data="tableData"
      :max-height="tableMaxHeight"
      @add="handleAddItem"
      @remove="handleRemoveItem" />
    <BkCheckbox
      v-model="isForce"
      v-bk-tooltips="$t('如忽略_有连接的情况下也会执行')"
      class="mb-20"
      :false-label="false">
      <span
        class="inline-block"
        style="margin-top: -2px; border-bottom: 1px dashed #979ba5">
        {{ $t('忽略业务连接') }}
      </span>
    </BkCheckbox>
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleReset">
        {{ $t('重置') }}
      </BkButton>
    </template>
  </SmartAction>
  <BatchInput
    v-model:is-show="isShowBatchInput"
    @change="handleBatchInput" />
  <ClusterSelector
    v-model:is-show="isShowBatchSelector"
    :tab-list="clusterSelectorTabList"
    @change="handleBatchSelectorChange" />
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getClusterInfoByDomains } from '@services/source/mysqlCluster';
  import { getClusterDatabaseNameList } from '@services/source/remoteService';
  import { createTicket } from '@services/source/ticket';
  import type { ResourceItem } from '@services/types';

  import { useInfo, useTableMaxHeight } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/ClusterSelector.vue';
  import type { ClusterSelectorResult } from '@components/cluster-selector/types';
  import SuccessView from '@components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@components/mysql-toolbox/ToolboxTable.vue';

  import { generateId } from '@utils';

  import BatchInput from './components/BatchInput.vue';

  import { useGlobalBizs } from '@/stores';

  interface TableItem {
    cluster_id: number,
    cluster_domain: string,
    from_database: string,
    to_database: string,
    uniqueId: string
  }
  interface TableColumnData {
    index: number,
    data: TableItem
  }
  interface ClusterDBNameInfo {
    databases: Array<string>,
    systemDatabases: Array<string>,
  }

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(334);

  const clusterSelectorTabList = [ClusterTypes.TENDBHA];
  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const clusterDBNameMap: Map<number, ClusterDBNameInfo> = reactive(new Map());
  const clusterInfoMap: Map<string, ResourceItem> = reactive(new Map());
  const isForce = ref(false);
  const tableData = ref<Array<TableItem>>([getTableItem()]);
  const clusterRules = [
    {
      validator: (value: string) => !!value,
      message: t('请输入集群'),
      trigger: 'blur',
    },
    {
      validator: verifyCluster,
      message: t('集群不存在'),
      trigger: 'blur',
    },
  ];
  const columns = [
    {
      label: () => (
        <span>
          { t('目标集群') }
          <db-icon type="batch-host-select" onClick={() => isShowBatchSelector.value = true} />
        </span>
      ),
      field: 'cluster_domain',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_cluster`}
          error-display-type="tooltips"
          rules={clusterRules}
          property={`${index}.cluster_domain`}>
          <bk-input
            v-model={[data.cluster_domain, ['trim']]}
            placeholder={t('请输入集群域名')}
            onBlur={hanldeDomainBlur.bind(null, index)} />
        </bk-form-item>
      ),
    },
    {
      label: t('源DB名'),
      field: 'from_database',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_from_database`}
          error-display-type="tooltips"
          rules={getFromDatabaseRules(data)}
          property={`${index}.from_database`}>
          <bk-input v-model={[data.from_database, ['trim']]} placeholder={t('请输入xx', [t('源DB名')])} />
        </bk-form-item>
      ),
    },
    {
      label: t('新DB名'),
      field: 'to_database',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_to_database`}
          error-display-type="tooltips"
          rules={getToDatabaseRules(data)}
          property={`${index}.to_database`}>
          <bk-input
            v-model={[data.to_database, ['trim']]}
            placeholder={t('请输入新DB名')}
            maxlength={40} />
        </bk-form-item>
      ),
    },
  ];

  /**
   * 获取表格数据
   */
  function getTableItem(): TableItem {
    return {
      cluster_id: 0,
      cluster_domain: '',
      from_database: '',
      to_database: '',
      uniqueId: generateId('CLONE_INSTANCE_'),
    };
  }

  /**
   * 设置集群 id
   */
  function hanldeDomainBlur(index: number) {
    const item = tableData.value[index];
    const info = clusterInfoMap.get(item.cluster_domain);
    item.cluster_id = info?.id ?? 0;
  }

  /**
   * 获取源 DB 名校验规则
   */
  function getFromDatabaseRules(data: TableItem) {
    return [
      {
        validator: () => data.cluster_id,
        message: t('请完善集群域名'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => !!value,
        message: t('请输入源DB名'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => verifyDBName(data, value),
        message: t('源DB名不存在'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => isSystemDBName(data, value),
        message: t('系统库不允许重命名'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => {
          const { cluster_domain: domain, uniqueId } = data;
          return !tableData.value.find((item) => {
            const {
              from_database: curFromDatabase,
              cluster_domain: curDomain,
              uniqueId: curUniqueId,
            } = item;
            return curUniqueId !== uniqueId && domain === curDomain && value === curFromDatabase;
          });
        },
        message: t('该源DB名已经存在于修改列表中'),
        trigger: 'blur',
      },
    ];
  }

  /**
   * 获取新 DB 名校验规则
   */
  function getToDatabaseRules(data: TableItem) {
    return [
      {
        validator: () => data.cluster_id,
        message: t('请完善集群域名'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => !!value,
        message: t('请输入新DB名'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => !value.startsWith('stage_truncate'),
        message: t('不可以stage_truncate开头'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => !value.endsWith('dba_rollback'),
        message: t('不可以dba_rollback结尾'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => /^[a-zA-z][a-zA-Z0-9_-]{1,39}$/.test(value),
        message: t('由字母_数字_下划线_减号_字符组成以字母开头'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => verifyDBRename(data, value),
        message: t('新DB名已存在于集群中'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => {
          const { cluster_domain: domain, uniqueId } = data;
          return !tableData.value.find((item) => {
            const {
              to_database: curToDatabase,
              cluster_domain: curDomain,
              uniqueId: curUniqueId,
            } = item;
            return curUniqueId !== uniqueId && domain === curDomain && value === curToDatabase;
          });
        },
        message: t('该新DB名已经存在于修改列表中'),
        trigger: 'blur',
      },
    ];
  }

  /**
   * 根据集群域名获取集群信息
   */
  function fetchClusterInfoByDomains() {
    const domains: Array<{ immute_domain: string }> = [];
    for (const item of tableData.value) {
      if (item.cluster_domain && !clusterInfoMap.get(item.cluster_domain)) {
        domains.push({ immute_domain: item.cluster_domain });
        continue;
      }

      const clusterInfo = clusterInfoMap.get(item.cluster_domain);
      if (clusterInfo) {
        item.cluster_id = clusterInfo.id;
      }
    }

    if (domains.length === 0) return Promise.resolve();

    return getClusterInfoByDomains({
      bizId: globalBizsStore.currentBizId,
      cluster_filters: _.uniq(domains) })
      .then((res) => {
        for (const item of res) {
          clusterInfoMap.set(item.master_domain, item);

          // 设置集群 id
          const list = tableData.value.filter(tableItem => tableItem.cluster_domain === item.master_domain);
          for (const tableItem of list) {
            tableItem.cluster_id = item.id;
          }
        }
        return res;
      });
  }

  /**
   * 获取集群 DB 名称
   */
  function fetchClusterDBNames() {
    const ids = tableData.value.map(item => item.cluster_id).filter(id => id);
    return getClusterDatabaseNameList({
      cluster_ids: ids,
    })
      .then((res) => {
        for (const item of res) {
          const { cluster_id, databases } = item;
          clusterDBNameMap.set(cluster_id, {
            databases,
            systemDatabases: item.system_databases,
          });
        }

        return res;
      });
  }

  /**
   * 校验集群域名是否存在
   */
  function verifyCluster(value: string) {
    const clusterInfo = clusterInfoMap.get(value);
    if (clusterInfo?.master_domain) {
      return true;
    }

    return fetchClusterInfoByDomains().then(() => Boolean(clusterInfoMap.get(value)?.master_domain));
  }

  /**
   * 获取集群的 DB names
   */
  function getDBNames(clusterId: number, key: keyof ClusterDBNameInfo) {
    return clusterDBNameMap.get(clusterId)?.[key] || [];
  }

  function getBuiltinDatabases(clusterId: number) {
    const databases = getDBNames(clusterId, 'databases');
    const systemdatabases = getDBNames(clusterId, 'systemDatabases');

    return [...databases, ...systemdatabases];
  }

  function isSystemDBName(data: TableItem, value: string) {
    if (getDBNames(data.cluster_id, 'systemDatabases').includes(value)) {
      return false;
    }

    return fetchClusterDBNames().then(() => !getDBNames(data.cluster_id, 'systemDatabases').includes(value));
  }

  /**
   * 校验源 DB 名是否存在于集群中
   */
  function verifyDBName(data: TableItem, value: string) {
    if (getBuiltinDatabases(data.cluster_id).includes(value)) {
      return true;
    }

    return fetchClusterDBNames().then(() => getBuiltinDatabases(data.cluster_id).includes(value));
  }

  /**
   * 校验新 DB 名是否存在于集群中
   */
  function verifyDBRename(data: TableItem, value: string) {
    if (getBuiltinDatabases(data.cluster_id).includes(value)) {
      return false;
    }

    return fetchClusterDBNames().then(() => !getBuiltinDatabases(data.cluster_id).includes(value));
  }

  /**
   * 批量添加若只有一行且为空则清空
   */
  function clearEmptyTableData() {
    if (tableData.value.length === 1) {
      const data = tableData.value[0];
      if (Object.values({ ...data, uniqueId: '' }).every(value => !value)) {
        tableData.value = [];
      }
    }
  }

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<{ domain: string, origin: string, rename: string }>) {
    const formatList = list.map(item => ({
      ...getTableItem(),
      cluster_domain: item.domain,
      from_database: item.origin,
      to_database: item.rename,
    }));
    clearEmptyTableData();
    tableData.value.push(...formatList);
    window.changeConfirm = true;

    try {
      await fetchClusterInfoByDomains();
      await fetchClusterDBNames();
    } catch (e) {
      console.log(e);
    }

    // 触发表格校验
    toolboxTableRef.value.validate();
  }

  function handleAddItem(index: number) {
    tableData.value.splice(index + 1, 0, getTableItem());
  }

  function handleRemoveItem(index: number) {
    tableData.value.splice(index, 1);
  }

  /**
   * 集群选择器批量选择
   */
  function handleBatchSelectorChange(selected: ClusterSelectorResult) {
    const list: Array<TableItem> = [];
    for (const key of Object.keys(selected)) {
      const formatList = selected[key].map((item) => {
        clusterInfoMap.set(item.master_domain, item);
        return {
          ...getTableItem(),
          cluster_domain: item.master_domain,
          cluster_id: item.id,
        };
      });
      list.push(...formatList);
    }

    clearEmptyTableData();
    tableData.value.push(...list);
    window.changeConfirm = true;
  }

  function handleReset() {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        tableData.value = [getTableItem()];
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }

  function handleSubmit() {
    toolboxTableRef.value.validate()
      .then(() => {
        isSubmitting.value = true;
        const params = {
          ticket_type: TicketTypes.MYSQL_HA_RENAME_DATABASE,
          bk_biz_id: globalBizsStore.currentBizId,
          details: {
            infos: tableData.value.map(item => ({
              cluster_id: item.cluster_id,
              from_database: item.from_database,
              to_database: item.to_database,
              force: isForce.value,
            })),
          },
        };
        createTicket(params)
          .then((res) => {
            ticketId.value = res.id;
            tableData.value = [getTableItem()];
            nextTick(() => {
              window.changeConfirm = false;
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      });
  }

  function handleCloseSuccess() {
    ticketId.value = 0;
  }
</script>

<style lang="less" scoped>
  .db-rename {
    height: 100%;
    overflow: hidden;

    .db-rename-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .db-rename-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }
  }
</style>
