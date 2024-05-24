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
        title: t('单据审批'),
        status: 'loading',
      },
      {
        title: t('清档_执行'),
      },
    ]"
    :ticket-id="ticketId"
    :title="t('清档任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="db-clear">
    <div class="pb-20">
      <BkAlert
        closable
        :title="t('清档_删除目标数据库数据_数据会暂存在不可见的备份库中_只有在执行删除备份库后_才会真正的删除数据')" />
      <div class="db-clear-operations">
        <BkButton
          class="db-clear-batch"
          @click="() => (isShowBatchInput = true)">
          <i class="db-icon-add" />
          {{ t('批量录入') }}
        </BkButton>
      </div>
      <ToolboxTable
        ref="toolboxTableRef"
        class="mb-20"
        :columns="columns"
        :data="tableData"
        :max-height="tableMaxHeight"
        @add="handleAddItem"
        @clone="handleCloneItem"
        @remove="handleRemoveItem" />
      <BkCheckbox
        v-model="isForce"
        v-bk-tooltips="t('安全模式下_存在业务连接时需要人工确认')"
        :false-label="1"
        :true-label="0">
        <span
          class="inline-block"
          style="margin-top: -2px; border-bottom: 1px dashed #979ba5">
          {{ t('安全模式') }}
        </span>
      </BkCheckbox>
      <TicketRemark v-model="remark" />
    </div>
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleReset">
        {{ t('重置') }}
      </BkButton>
    </template>
  </SmartAction>
  <BatchInput
    v-model:is-show="isShowBatchInput"
    @change="handleBatchInput" />
  <ClusterSelector
    v-model:is-show="isShowBatchSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    only-one-type
    :selected="selectedClusters"
    @change="handleBatchSelectorChange" />
  <div
    v-show="isShowInputTips"
    ref="popRef"
    style="font-size: 12px; line-height: 24px; color: #63656e">
    <p>{{ t('匹配任意长度字符串_如a_不允许独立使用') }}</p>
    <p>{{ t('匹配任意单一字符_如a_d') }}</p>
    <p>{{ t('专门指代ALL语义_只能独立使用') }}</p>
    <p>{{ t('注_含通配符的单元格仅支持输入单个对象') }}</p>
    <p>{{ t('Enter完成内容输入') }}</p>
  </div>
</template>

<script setup lang="tsx">
  import type FormItem from 'bkui-vue/lib/form/form-item';
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import type { Instance, SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getClusterInfoByDomains } from '@services/source/mysqlCluster';
  import { getClusterDatabaseNameList } from '@services/source/remoteService';
  import { createTicket } from '@services/source/ticket';

  import {
    useTableMaxHeight,
    useTicketCloneInfo,
  } from '@hooks';

  import {
    ClusterTypes,
    TicketTypes,
  } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import BatchEditColumn from '@components/batch-edit-column/Index.vue';
  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import SuccessView from '@components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@components/mysql-toolbox/ToolboxTable.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import { generateId, messageError } from '@utils';

  import { truncateDataTypes } from './common/const';
  import type { InputItem } from './common/types';
  import BatchInput from './components/BatchInput.vue';

  import { useGlobalBizs } from '@/stores';

  type FormItemInstance = InstanceType<typeof FormItem>;

  interface TableItem {
    cluster_domain: string,
    cluster_id: number,
    cluster_type: string,
    db_patterns: string[],
    ignore_dbs: string[],
    table_patterns: string[],
    ignore_tables: string[],
    truncate_data_type: string,
    uniqueId: string
  }

  type IDataRowBatchKey = keyof Omit<TableItem, 'cluster_domain' | 'cluster_id' | 'cluster_type' | 'uniqueId'>

  interface TableColumnData {
    index: number,
    data: TableItem
  }

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(334);

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_HA_TRUNCATE_DATA,
    onSuccess(cloneData) {
      const {
        tableDataList,
      } = cloneData;
      tableData.value = tableDataList;
      remark.value = cloneData.remark
      window.changeConfirm = true;
    },
  });

  let tippyInst:Instance | undefined;

  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const isForce = ref(1);
  const popRef = ref<HTMLDivElement>();
  const isShowInputTips = ref(false);
  const tableData = ref<Array<TableItem>>([getTableItem()]);
  const remark = ref('')

  const selectedClusters = shallowRef<{[key: string]: Array<TendbhaModel>}>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const batchEditShow = reactive({
    db_patterns: false,
    ignore_dbs: false,
    table_patterns: false,
    ignore_tables: false,
    truncate_data_type: false,
  });

  const clusterInfoMap: Map<string, TendbhaModel> = reactive(new Map());
  const clusterDBNameMap: Map<number, Array<string>> = reactive(new Map());

  // 设置 target|source form-item
  const formItemRefs: Map<string, FormItemInstance> = reactive(new Map());

  const rules = {
    cluster: [
      {
        validator: (value: string) => !!value,
        message: t('请输入xx', [t('集群')]),
        trigger: 'blur',
      },
      {
        validator: verifyCluster,
        message: t('集群不存在'),
        trigger: 'blur',
      },
    ],
    truncate: [
      {
        validator: (value: string) => !!value,
        message: t('请选择'),
        trigger: 'blur',
      },
    ],
  };

  const columns = [
    {
      label: () => (
        <span class="column-required">
          {t('目标集群')}
          <db-icon type="batch-host-select" onClick={() => isShowBatchSelector.value = true} />
        </span>
      ),
      field: 'cluster_domain',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_cluster`}
          error-display-type="tooltips"
          rules={rules.cluster}
          property={`${index}.cluster_domain`}>
          <bk-input
            data={data}
            v-model={[data.cluster_domain, ['trim']]}
            placeholder={t('请输入xx', [t('集群域名')])}
            onBlur={hanldeDomainBlur.bind(null, index)}
          />
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span>
          { t('清档类型') }
          <BatchEditColumn
            model-value={batchEditShow.truncate_data_type}
            title={t('清档类型')}
            data-list={truncateDataTypes}
            onChange={(value) => handleBatchEditChange(value, 'truncate_data_type')}>
            <span
              v-bk-tooltips={t('统一设置：将该列统一设置为相同的值')}
              class="ml-4"
              style="color: #3A84FF"
              onClick={() => handleBatchEditShow('truncate_data_type')}>
              <db-icon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </span>
      ),
      field: 'truncate_data_type',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_truncate_data_type`}
          error-display-type="tooltips"
          rules={rules.truncate}
          property={`${index}.truncate_data_type`}>
          <bk-select
            v-model={data.truncate_data_type}
            list={truncateDataTypes}
            clearable={false}
            popoverMinWidth={200}
            onChange={handleSelectedTruncate.bind(null, index)}
          />
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span>
          { t('目标DB名') }
          <BatchEditColumn
            model-value={batchEditShow.db_patterns}
            title={t('目标DB名')}
            type='taginput'
            onChange={(value) => handleBatchEditChange(value, 'db_patterns')}>
            <span
              v-bk-tooltips={t('统一设置：将该列统一设置为相同的值')}
              class="ml-4"
              style="color: #3A84FF"
              onClick={() => handleBatchEditShow('db_patterns')}>
              <db-icon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </span>
      ),
      field: 'db_patterns',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_db_patterns`}
          error-display-type="tooltips"
          rules={getPatterns('db', index)}
          property={`${index}.db_patterns`}>
          <bk-tag-input
            v-model={data.db_patterns}
            allow-auto-match
            allow-create
            clearable={false}
            paste-fn={tagInputPasteFn}
            has-delete-icon
            collapse-tags
            placeholder={t('请输入')}
            onClick={handleShowTips}
            v-clickoutside={handleHideTips}
          />
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span>
          { t('目标表名') }
          <BatchEditColumn
            model-value={batchEditShow.table_patterns}
            title={t('目标表名')}
            type='taginput'
            onChange={(value) => handleBatchEditChange(value, 'table_patterns')}>
            <span
              v-bk-tooltips={t('统一设置：将该列统一设置为相同的值')}
              class="ml-4"
              style="color: #3A84FF"
              onClick={() => handleBatchEditShow('table_patterns')}>
              <db-icon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </span>
      ),
      field: 'table_patterns',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          ref={setFormItemRefs.bind(null, `${data.uniqueId}_table_patterns_${index}`)}
          key={`${data.uniqueId}_table_patterns`}
          error-display-type="tooltips"
          rules={getPatterns('table', index)}
          property={`${index}.table_patterns`}>
          <bk-tag-input
            v-model={data.table_patterns}
            allow-auto-match
            disabled={data.truncate_data_type === 'drop_database'}
            allow-create
            clearable={false}
            paste-fn={tagInputPasteFn}
            has-delete-icon
            collapse-tags
            placeholder={t('请输入')}
            onClick={handleShowTips}
            v-clickoutside={handleHideTips}
          />
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span>
          { t('忽略DB名') }
          <BatchEditColumn
            model-value={batchEditShow.ignore_dbs}
            title={t('忽略DB名')}
            type='taginput'
            onChange={(value) => handleBatchEditChange(value, 'ignore_dbs')}>
            <span
              v-bk-tooltips={t('统一设置：将该列统一设置为相同的值')}
              class="ml-4"
              style="color: #3A84FF"
              onClick={() => handleBatchEditShow('ignore_dbs')}>
              <db-icon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </span>
      ),
      field: 'ignore_dbs',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_ignore_dbs`}
          error-display-type="tooltips"
          rules={getIgnorePatterns('db', index)}
          property={`${index}.ignore_dbs`}>
          <bk-tag-input
            v-model={data.ignore_dbs}
            allow-create
            clearable={false}
            paste-fn={tagInputPasteFn}
            has-delete-icon
            collapse-tags
            placeholder={t('请输入')}
            onClick={handleShowTips}
            v-clickoutside={handleHideTips}
          />
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span>
          { t('忽略表名') }
          <BatchEditColumn
            model-value={batchEditShow.ignore_tables}
            title={t('忽略表名')}
            type='taginput'
            onChange={(value) => handleBatchEditChange(value, 'ignore_tables')}>
            <span
              v-bk-tooltips={t('统一设置：将该列统一设置为相同的值')}
              class="ml-4"
              style="color: #3A84FF"
              onClick={() => handleBatchEditShow('ignore_tables')}>
              <db-icon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </span>
      ),
      field: 'ignore_tables',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          ref={setFormItemRefs.bind(null, `${data.uniqueId}_ignore_tables_${index}`)}
          key={`${data.uniqueId}_ignore_tables`}
          error-display-type="tooltips"
          rules={getIgnorePatterns('table', index)}
          property={`${index}.ignore_tables`}>
          <bk-tag-input
            v-model={data.ignore_tables}
            disabled={data.truncate_data_type === 'drop_database'}
            allow-create
            clearable={false}
            paste-fn={tagInputPasteFn}
            has-delete-icon
            collapse-tags
            placeholder={t('请输入')}
            onClick={handleShowTips}
            v-clickoutside={handleHideTips}
          />
        </bk-form-item>
      ),
    },
  ];

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const tagInputPasteFn = (value: string) => value.split('\n').map(item => ({ id: item }));

  // 检测列表是否为空
  const checkListEmpty = (list: Array<TableItem>) => {
    if (list.length > 1) {
      return false;
    }

    const [firstRow] = list;
    return !firstRow?.cluster_domain;
  };

  function setFormItemRefs(key: string, vueInstance: FormItemInstance) {
    if (vueInstance) {
      formItemRefs.set(key, vueInstance);
    } else {
      formItemRefs.delete(key);
    }
  }

  /**
   * 获取表格数据
   */
  function getTableItem(): TableItem {
    return {
      cluster_domain: '',
      cluster_type: '',
      cluster_id: 0,
      db_patterns: [],
      ignore_dbs: [],
      table_patterns: [],
      ignore_tables: [],
      truncate_data_type: '',
      uniqueId: generateId('SLAVE_ADD_'),
    };
  }

  /**
   * 设置输入框 tips
   */
  function handleShowTips(e: PointerEvent) {
    handleHideTips();

    const target = (e.target as HTMLElement).closest('.bk-tag-input') || e.target;
    tippyInst = dbTippy(target as SingleTarget, {
      content: popRef.value,
      placement: 'top',
      appendTo: () => document.body,
      theme: 'light',
      trigger: 'manual',
      maxWidth: 'none',
      interactive: true,
      arrow: true,
      offset: [0, 8],
      zIndex: 999999,
      hideOnClick: false,
    });
    isShowInputTips.value = true;
    nextTick(() => {
      tippyInst?.show?.();
    });
  }

  /**
   * 隐藏输入框 tips
   */
  function handleHideTips() {
    isShowInputTips.value = false;
    if (tippyInst) {
      tippyInst.hide();
      tippyInst.unmount();
      tippyInst.destroy();
      tippyInst = undefined;
    }
  }

  // 选择清档类型
  function handleSelectedTruncate(index: number, value: string) {
    const data = tableData.value[index];
    // 清档类型为删除数据库，则不需要填写表相关内容，并设置为 *
    if (value === 'drop_database') {
      data.table_patterns = ['*'];
      data.ignore_tables = ['*'];
      const tableRef = formItemRefs.get(`${data.uniqueId}_table_patterns_${index}`);
      const ignoreRef = formItemRefs.get(`${data.uniqueId}_ignore_tables_${index}`);
      tableRef && tableRef.clearValidate();
      ignoreRef && ignoreRef.clearValidate();
    } else {
      data.table_patterns = [];
      data.ignore_tables = [];
    }
  }

  /**
   * 设置集群 id
   */
  function hanldeDomainBlur(index: number) {
    const item = tableData.value[index];
    const info = clusterInfoMap.get(item.cluster_domain);
    item.cluster_id = info?.id ?? 0;
  }

  function getDBMessage(index: number, key: 'db_patterns' | 'ignore_dbs') {
    const data = tableData.value[index];
    const value = data[key];
    const clusterDBs = getDBNames(data.cluster_id);
    const values = value.map(val => val.trim()).filter(val => val);
    const notExist: string[] = [];
    for (const val of values) {
      if (!clusterDBs.includes(val)) {
        notExist.push(val);
      }
    }
    return t('集群中不存在xx', [notExist.join('、')]);
  }

  /**
   * 获取 db\table 校验规则
   */
  function getPatterns(type: 'db' | 'table', index: number) {
    const data = tableData.value[index];
    const label = type === 'db' ? t('指定DB名') : t('指定表名');
    const isDBType = data.truncate_data_type === 'drop_database' && type === 'table';
    const extra = type === 'db' ? [
      {
        validator: (value: string[]) => {
          const values = value.map(val => val.trim()).filter(val => val);
          return values.every(val =>  /^[a-zA-Z0-9_%*?-]+$/.test(val));
        },
        message: t('只允许输入通配符_大小写字母_数字_下划线_连接符'),
        trigger: 'blur',
      },
      {
        validator: () => data.cluster_id,
        message: t('请完善集群域名'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => (value.some(val => /[%*?]/.test(val)) ? true : verifyDBName(data, value)),
        message: getDBMessage(index, 'db_patterns'),
        trigger: 'blur',
      },
    ] : [];
    return [
      {
        validator: (value: string[]) => (isDBType ? true : value.length !== 0),
        message: t('请输入xx', [label]),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => (isDBType ? true : value.every(val => val.trim() !== '%')),
        message: t('通配符_不允许单独使用'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => {
          if (isDBType) return true;
          return !value.some(val => val.trim().includes('*') && val.length !== 1);
        },
        message: t('通配符_不允许组合使用'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => {
          if (isDBType || value.every(val => !/[%*?]/.test(val))) return true;
          return value.length === 1;
        },
        message: t('包含通配符_不允许输入多个对象'),
        trigger: 'blur',
      },
      ...extra,
    ];
  }

  /**
   * 获取 ignore db\table 校验规则
   */
  function getIgnorePatterns(type: 'db' | 'table', index: number) {
    const data = tableData.value[index];
    const extra = type === 'db' ? [
      {
        validator: (value: string[]) => {
          const values = value.map(val => val.trim()).filter(val => val);
          if (value.length === 0 || values.length === 0) return true;
          return values.every(val => /^[a-zA-Z0-9_%*?-]+$/.test(val));
        },
        message: t('只允许输入通配符_大小写字母_数字_下划线_连接符'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => value.length === 0 || data.cluster_id,
        message: t('请完善集群域名'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => {
          if (value.length === 0) return true;
          return value.some(val => /[%*?]/.test(val)) ? true : verifyDBName(data, value);
        },
        message: getDBMessage(index, 'ignore_dbs'),
        trigger: 'blur',
      },
    ] : [];
    return [
      {
        validator: () => {
          // 清档类型为删除数据库则不需要校验此项
          if (data.truncate_data_type === 'drop_database') {
            return true;
          }
          // 要么同时为空、要么同时填写
          if (
            (data.ignore_dbs.length > 0 && data.ignore_tables.length > 0)
            || (data.ignore_dbs.length === 0 && data.ignore_tables.length === 0)
          ) {
            return true;
          }
          return false;
        },
        message: t('忽略DB名和忽略表名必须同时填写或者同时为空'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => value.length === 0 || value.every(val => val.trim() !== '%'),
        message: t('通配符_不允许单独使用'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => {
          if (value.length === 0) return true;
          return !value.some(val => val.trim().includes('*') && val.length !== 1);
        },
        message: t('通配符_不允许组合使用'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => {
          if (value.length === 0 || value.every(val => !/[%*?]/.test(val))) return true;
          return value.length === 1;
        },
        message: t('包含通配符_不允许输入多个对象'),
        trigger: 'blur',
      },
      ...extra,
    ];
  }

  /**
   * 校验集群域名是否存在
   */
  function verifyCluster(value: string) {
    const clusterInfo = clusterInfoMap.get(value);
    if (clusterInfo?.master_domain) {
      return true;
    }

    return fetchClusterInfoByDomains().then(() => Boolean(clusterInfoMap.get(value)?.id));
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
      cluster_filters: _.uniq(domains),
    })
      .then((res) => {
        for (const item of res) {
          clusterInfoMap.set(item.master_domain, item);

          // 设置集群 id
          const list = tableData.value.filter(tableItem => tableItem.cluster_domain === item.master_domain);
          for (const tableItem of list) {
            tableItem.cluster_id = item.id;
            tableItem.cluster_type = item.cluster_type;
          }
        }

        return res;
      });
  }

  /**
   * 获取集群的 DB names
   */
  function getDBNames(clusterId: number) {
    return clusterDBNameMap.get(clusterId) || [];
  }

  /**
   * 校验源 DB 名是否存在于集群中
   */
  function verifyDBName(data: TableItem, value: string[]) {
    const values = value.map(val => val.trim()).filter(val => val);
    if (values.every(val => getDBNames(data.cluster_id).includes(val))) {
      return true;
    }

    return fetchClusterDBNames().then(() => values.every(val => getDBNames(data.cluster_id).includes(val)));
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
          clusterDBNameMap.set(cluster_id, databases);
        }
        return res;
      });
  }

  /**
   * 集群选择器批量选择
   */
  function handleBatchSelectorChange(selected: Record<string, Array<TendbhaModel>>) {
    selectedClusters.value = selected;
    const newList: TableItem[] = [];
    const selectedList = Object.keys(selected).reduce(
      (list: TendbhaModel[], key) => list.concat(...selected[key]),
      [],
    );
    selectedList.forEach((item) => {
      const domain = item.master_domain;
      clusterInfoMap.set(domain, item);
      if (!domainMemo[domain]) {
        const row = {
          ...getTableItem(),
          cluster_domain: domain,
          cluster_id: item.id,
          cluster_type: item.cluster_type,
        };
        newList.push(row);
        domainMemo[domain] = true;
      }
    });

    clearEmptyTableData();
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  }

  /**
   * 批量添加若只有一行且为空则清空
   */
  function clearEmptyTableData() {
    if (tableData.value.length === 1) {
      const data = tableData.value[0];
      if (Object.values({ ...data, uniqueId: '' }).every(value => (Array.isArray(value) ? !value.length : !value))) {
        tableData.value = [];
      }
    }
  }

  const handleBatchEditShow = (key: IDataRowBatchKey) => {
    batchEditShow[key] = !batchEditShow[key];
  };

  const handleBatchEditChange = (value: string | string[], filed: IDataRowBatchKey) => {
    if (!value || checkListEmpty(tableData.value)) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, {
        [filed]: value,
      });
    });
  };

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<InputItem>) {
    const formatList = list.map(item => ({
      ...getTableItem(),
      cluster_domain: item.cluster,
      db_patterns: item.dbs,
      ignore_dbs: item.ignoreDBs,
      table_patterns: item.tables,
      ignore_tables: item.ignoreTables,
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
    const dataList = [...tableData.value];
    const domain = dataList[index].cluster_domain;
    if (domain) {
      clusterInfoMap.delete(domain);
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
      selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter(item => item.master_domain !== domain);
    }
    tableData.value.splice(index, 1);
  }

  const handleCloneItem = (index: number) => {
    tableData.value.splice(index + 1, 0, _.cloneDeep(tableData.value[index]));
    setTimeout(() => {
      toolboxTableRef.value.validate();
    })
  }

  function handleReset() {
    InfoBox({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      cancelText: t('取消'),
      onConfirm: () => {
        tableData.value = [getTableItem()];
        remark.value = ''
        selectedClusters.value[ClusterTypes.TENDBHA] = [];
        selectedClusters.value[ClusterTypes.TENDBSINGLE] = [];
        clusterInfoMap.clear();
        domainMemo = {};
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
        const clusterTypes = _.uniq(tableData.value.map(item => item.cluster_type));
        // 限制只能提同一种类型的集群，否则提示
        if (clusterTypes.length > 1) {
          messageError('只允许提交一种集群类型');
          return;
        }

        isSubmitting.value = true;
        const formatList = (values: string[]) => values.map(val => val.trim()).filter(val => val);
        const params = {
          ticket_type: clusterTypes[0] === ClusterTypes.TENDBHA
            ? TicketTypes.MYSQL_HA_TRUNCATE_DATA : TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA,
          bk_biz_id: globalBizsStore.currentBizId,
          remark: remark.value,
          details: {
            infos: tableData.value.map(item => ({
              cluster_id: item.cluster_id,
              truncate_data_type: item.truncate_data_type,
              db_patterns: formatList(item.db_patterns),
              ignore_dbs: formatList(item.ignore_dbs),
              // drop_database 类型默认传 *
              table_patterns: item.truncate_data_type === 'drop_database' ? ['*'] : formatList(item.table_patterns),
              ignore_tables: formatList(item.ignore_tables),
              force: Boolean(isForce.value),
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

  onBeforeUnmount(() => {
    handleHideTips();
  });
</script>

<style lang="less" scoped>
  .db-clear {
    height: 100%;
    overflow: hidden;

    .db-clear-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .db-clear-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }
  }
</style>
