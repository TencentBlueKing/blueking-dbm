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
    :steps="successTipSteps"
    :ticket-id="ticketId"
    :title="$t('数据校验修复任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="checksum">
    <BkAlert
      closable
      :title="$t('数据校验修复_对集群的主库和从库进行数据一致性校验和修复_其中MyISAM引擎库表不会被校验和修复')" />
    <BkButton
      class="checksum-batch"
      @click="() => isShowBatchInput = true">
      <i class="db-icon-add" />
      {{ $t('批量录入') }}
    </BkButton>
    <div class="checksum-main">
      <ToolboxTable
        ref="toolboxTableRef"
        :columns="columns"
        :data="tableData"
        :max-height="tableMaxHeight"
        @add="handleAddItem"
        @remove="handleRemoveItem" />
      <DbForm
        ref="checksumFormRef"
        class="checksum-form"
        form-type="vertical"
        :model="formdata">
        <BkFormItem
          :label="$t('定时执行时间')"
          property="timing"
          required>
          <BkDatePicker
            v-model="formdata.timing"
            class="not-seconds-date-picker"
            :disabled-date="disabledDate"
            :placeholder="$t('请选择xx', [$t('定时执行时间')])"
            style="width: 100%;"
            type="datetime" />
        </BkFormItem>
        <BkFormItem
          :label="$t('全局超时时间')"
          property="runtime_hour"
          required>
          <BkInput
            v-model="formdata.runtime_hour"
            :max="168"
            :min="24"
            type="number" />
        </BkFormItem>
        <BkFormItem
          :label="$t('数据修复')"
          required>
          <BkSwitcher
            v-model="formdata.data_repair.is_repair"
            theme="primary" />
        </BkFormItem>
        <BkFormItem
          v-if="formdata.data_repair.is_repair"
          :label="$t('修复模式')"
          required>
          <BkRadioGroup
            v-model="formdata.data_repair.mode"
            class="repair-mode">
            <div class="item-box">
              <BkRadio label="manual">
                <div class="item-content">
                  <DbIcon
                    class="item-flag"
                    type="account" />
                  <div class="item-label">
                    {{ $t('人工确认') }}
                  </div>
                  <div>{{ $t('校验检查完成需人工确认后_方可执行修复动作') }}</div>
                </div>
              </BkRadio>
            </div>
            <div class="item-box">
              <BkRadio label="auto">
                <div class="item-content">
                  <DbIcon
                    class="item-flag"
                    type="timed-task" />
                  <div class="item-label">
                    {{ $t('自动修复') }}
                  </div>
                  <div>{{ $t('校验检查完成后_将自动修复数据') }}</div>
                </div>
              </BkRadio>
            </div>
          </BkRadioGroup>
        </BkFormItem>
      </DbForm>
    </div>
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
    :tab-list="['tendbha']"
    @change="handleBatchSelectorChange" />
  <div
    v-show="isShowInputTips"
    ref="popRef"
    style=" font-size: 12px; line-height: 24px;color: #63656e;">
    <p>{{ $t('匹配任意长度字符串_如a_不允许独立使用') }}</p>
    <p>{{ $t('匹配任意单一字符_如a_d') }}</p>
    <p>{{ $t('专门指代ALL语义_只能独立使用') }}</p>
    <p>{{ $t('注_含通配符的单元格仅支持输入单个对象') }}</p>
    <p>{{ $t('Enter完成内容输入') }}</p>
  </div>
</template>

<script setup lang="tsx">
  import type FormItem from 'bkui-vue/lib/form/form-item';
  import { format } from 'date-fns';
  import _ from 'lodash';
  import type { Instance, SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  // TODO INTERFACE done
  // import {
  //   checkInstances,
  //   getClusterInfoByDomains,
  // } from '@services/clusters';
  // import { getClusterDBNames } from '@services/remoteService';
  // import { createTicket } from '@services/ticket';
  import { checkInstances } from '@services/source/instances';
  import { getClusterInfoByDomains } from '@services/source/mysqlCluster';
  import { getClusterDBNames } from '@services/source/remoteService';
  import { createTicket } from '@services/ticket';
  import type {
    InstanceInfos,
    ResourceItem,
    ResourceItemInstInfo,
  } from '@services/types/clusters';

  import {
    useInfo,
    useTableMaxHeight,
  } from '@hooks';

  import { TicketTypes } from '@common/const';
  import { ipPort } from '@common/regex';
  import { dbTippy } from '@common/tippy';

  import ClusterSelector from '@components/cluster-selector/ClusterSelector.vue';
  import type { ClusterSelectorResult } from '@components/cluster-selector/types';
  import SuccessView from '@components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@components/mysql-toolbox/ToolboxTable.vue';

  import { generateId } from '@utils';

  import type { InputItem } from './common/types';
  import BatchInput from './components/BatchInput.vue';

  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  type FormItemInstance = InstanceType<typeof FormItem>;

  interface TableItem {
    cluster_domain: string,
    cluster_id: number,
    db_patterns: string[],
    ignore_dbs: string[],
    table_patterns: string[],
    ignore_tables: string[],
    master: string,
    masterInstance: ResourceItemInstInfo,
    slaves: string[],
    slaveList: ResourceItemInstInfo[],
    uniqueId: string
  }
  interface TableColumnData {
    index: number,
    data: TableItem
  }

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(334);
  let tippyInst:Instance | undefined;
  const disabledDate = (date: Date | number) => {
    const day = new Date();
    day.setDate(day.getDate() - 1);
    const dateTime = typeof date === 'number' ? date : date.getTime();
    return dateTime < day.getTime();
  };
  const getCurrentDate = () => {
    const today = new Date();
    today.setSeconds(0);
    return today;
  };

  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const checksumFormRef = ref();
  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const popRef = ref<HTMLDivElement>();
  const isShowInputTips = ref(false);
  const clusterInfoMap: Map<string, ResourceItem> = reactive(new Map());
  const clusterDBNameMap: Map<number, Array<string>> = reactive(new Map());
  const instanceMap: Map<string, InstanceInfos> = reactive(new Map());
  const formdata = reactive({
    timing: getCurrentDate(),
    runtime_hour: 48,
    data_repair: {
      is_repair: true,
      mode: 'manual',
    },
  });
  const successTipSteps = computed(() => {
    const steps = [{
      title: t('单据审批'),
      status: 'loading',
    }, {
      title: t('数据校验_执行'),
    }];
    if (formdata.data_repair.is_repair && formdata.data_repair.mode === 'auto') {
      steps.push({
        title: t('数据修复_自动执行'),
      });
    } else {
      steps.push(...[{
        title: t('人工确认'),
      }, {
        title: t('数据修复_执行'),
      }]);
    }
    return steps;
  });
  const tableData = ref<Array<TableItem>>([getTableItem()]);
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
    slaves: [
      {
        validator: (values: string[]) => values.length > 0,
        message: t('请选择'),
        trigger: 'blur',
      },
    ],
  };
  const columns: TableProps['columns'] = [
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
        <span class="column-required">
          {t('校验主库')}
        </span>
      ),
      field: 'master',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_master`}
          error-display-type="tooltips"
          ref={setFormItemRefs.bind(null, 'master')}
          rules={getMasterRules(index)}
          property={`${index}.master`}>
          <bk-input v-model={[data.master, ['trim']]} placeholder={t('请输入xx', [' IP:Port'])} disabled={true} />
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span class="column-required">
          {t('校验从库')}
        </span>
      ),
      field: 'slaves',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_slaves`}
          error-display-type="tooltips"
          rules={rules.slaves}
          property={`${index}.slaves`}>
          <span v-bk-tooltips={{ content: t('请完善目标集群'), disabled: data.cluster_id > 0 }}>
            <bk-select
              v-model={data.slaves}
              disabled={data.cluster_id === 0}
              list={data.slaveList}
              idKey="instance"
              displayKey="instance"
              clearable={false}
              filterable
              multiple
              show-select-all
              collapse-tags
              multiple-mode="tag"
              popoverMinWidth={200}
            />
          </span>
        </bk-form-item>
      ),
    },
    {
      label: () => (
        <span class="column-required">
          {t('校验DB')}
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
            allow-create
            clearable={false}
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
        <span class="column-required">
          {t('校验表名')}
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
            allow-create
            clearable={false}
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
      label: t('忽略DB名'),
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
      label: t('忽略表名'),
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
            allow-create
            clearable={false}
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

  // 设置 target|source form-item
  const formItemRefs: Map<string, FormItemInstance> = reactive(new Map());
  function setFormItemRefs(key: string, vueInstance: FormItemInstance) {
    if (vueInstance) {
      formItemRefs.set(key, vueInstance);
    } else {
      formItemRefs.delete(key);
    }
  }

  function createInstanceData(): ResourceItemInstInfo {
    return {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      bk_instance_id: 0,
      ip: '',
      name: '',
      instance: '',
      port: 0,
      status: 'running',
    };
  }

  /**
   * 获取表格数据
   */
  function getTableItem(): TableItem {
    return {
      cluster_domain: '',
      cluster_id: 0,
      db_patterns: [],
      ignore_dbs: [],
      table_patterns: [],
      ignore_tables: [],
      master: '',
      masterInstance: createInstanceData(),
      slaves: [],
      slaveList: [],
      uniqueId: generateId('CHECKSUM_'),
    };
  }

  onBeforeUnmount(() => {
    handleHideTips();
  });

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

  /**
   * 设置集群 id
   */
  function hanldeDomainBlur(index: number) {
    const item = tableData.value[index];
    const info = clusterInfoMap.get(item.cluster_domain);
    item.slaves = [];
    if (info) {
      item.cluster_id = info.id;
      item.slaveList = info.slaves || [];
      item.master = info.masters[0]?.instance || '';
      item.masterInstance = info.masters[0] || createInstanceData();
    } else {
      item.cluster_id = 0;
      item.slaveList = [];
      item.master = '';
      item.masterInstance = createInstanceData();
    }
  }

  function getMasterRules(index: number) {
    const data = tableData.value[index];
    return [
      {
        validator: (inst: string) => ipPort.test(inst),
        message: t('请输入xx', [t('合法IP_Port')]),
        trigger: 'blur',
      },
      {
        validator: () => data.cluster_id,
        message: t('请完善集群域名'),
        trigger: 'blur',
      },
      {
        validator: verifyInstance,
        message: t('实例不存在'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => clusterInfoMap.get(data.cluster_domain)?.masters?.[0]?.instance === value,
        message: t('目标集群与校验主库不匹配'),
        trigger: 'blur',
      },
    ];
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
    const label = type === 'db' ? '校验 DB' : '校验表名';
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
        validator: (value: string[]) => value.length !== 0,
        message: t('请输入xx', [label]),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => value.every(val => val.trim() !== '%'),
        message: t('通配符_不允许单独使用'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => !value.some(val => val.trim().includes('*') && val.length !== 1),
        message: t('通配符_不允许组合使用'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => {
          if (value.every(val => !/[%*?]/.test(val))) return true;
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
        item.master = clusterInfo.masters[0]?.instance || '';
        item.masterInstance = clusterInfo.masters[0] || createInstanceData();
        item.slaveList = clusterInfo.slaves || [];
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
            tableItem.master = item.masters[0]?.instance || '';
            tableItem.masterInstance = item.masters[0] || createInstanceData();
            tableItem.slaveList = item.slaves || [];
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
    return getClusterDBNames({
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
   * 校验实例是否存在
   */
  function verifyInstance(value: string) {
    // 已经查询过且存在的实例
    const curInstanceInfo = instanceMap.get(value);
    if (curInstanceInfo?.cluster_id) {
      return true;
    }

    const instances = tableData.value.map(item => item.master).filter(inst => ipPort.test(inst.trim()));
    return fetchInstanceInfos(instances)
      .then(() => Boolean(instanceMap.get(value)?.cluster_id));
  }

  /**
   * 查询实例信息
   */
  function fetchInstanceInfos(instances: string[]) {
    return checkInstances({
      bizId: globalBizsStore.currentBizId,
      instance_addresses: instances,
    })
      .then((res) => {
        for (const item of res) {
          const { ip, port } = item;
          instanceMap.set(`${ip}:${port}`, item);
        }
        return res;
      });
  }

  /**
   * 集群选择器批量选择
   */
  function handleBatchSelectorChange(selected: ClusterSelectorResult) {
    const list: Array<TableItem> = [];
    for (const key of Object.keys(selected)) {
      const formatList = selected[key].map((item) => {
        clusterInfoMap.set(item.master_domain, item);
        const masterInfo = item.masters[0];
        return {
          ...getTableItem(),
          cluster_domain: item.master_domain,
          cluster_id: item.id,
          master: masterInfo ? `${masterInfo.ip}:${masterInfo.port}` : '',
          masterInstance: masterInfo || createInstanceData(),
          slaveList: item.slaves || [],
        };
      });
      list.push(...formatList);
    }

    clearEmptyTableData();
    tableData.value.push(...list);
    window.changeConfirm = true;
  }

  /**
   * 批量添加若只有一行且为空则清空
   */
  function clearEmptyTableData() {
    if (tableData.value.length === 1) {
      const data = tableData.value[0];
      if (Object.values({ ...data, uniqueId: '', masterInstance: '' }).every(value => (Array.isArray(value) ? !value.length : !value))) {
        tableData.value = [];
      }
    }
  }

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<InputItem>) {
    const formatList = list.map(item => ({
      ...getTableItem(),
      cluster_domain: item.cluster,
      master: item.master,
      slaves: item.slaves,
      db_patterns: item.dbs,
      ignore_dbs: item.ignoreDBs,
      table_patterns: item.tables,
      ignore_tables: item.ignoreTables,
    }));
    clearEmptyTableData();
    tableData.value.push(...formatList);
    window.changeConfirm = true;

    const instances = formatList.map(item => item.master);
    try {
      await fetchClusterInfoByDomains();
      await fetchClusterDBNames();
      await fetchInstanceInfos(instances);
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

  function handleReset() {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        tableData.value = [getTableItem()];
        formdata.data_repair.is_repair = true;
        formdata.timing = getCurrentDate();
        formdata.runtime_hour = 48;
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }

  function handleSubmit() {
    isSubmitting.value = true;
    Promise.all([checksumFormRef.value.validate(), toolboxTableRef.value.validate()])
      .then(() => {
        const formatList = (values: string[]) => values.map(val => val.trim()).filter(val => val);
        const formatInstance = (inst: ResourceItemInstInfo) => ({
          bk_biz_id: inst.bk_biz_id,
          bk_cloud_id: inst.bk_cloud_id,
          bk_host_id: inst.bk_host_id,
          ip: inst.ip,
          port: inst.port,
        });
        const params = {
          ticket_type: TicketTypes.MYSQL_CHECKSUM,
          bk_biz_id: globalBizsStore.currentBizId,
          details: {
            ...formdata,
            timing: format(new Date(formdata.timing), 'yyyy-MM-dd HH:mm:ss'),
            infos: tableData.value.map(item => ({
              cluster_id: item.cluster_id,
              master: formatInstance(item.masterInstance),
              slaves: item.slaveList
                .filter(inst => item.slaves.includes(inst.instance))
                .map(inst => formatInstance(inst)),
              db_patterns: formatList(item.db_patterns),
              ignore_dbs: formatList(item.ignore_dbs),
              table_patterns: formatList(item.table_patterns),
              ignore_tables: formatList(item.ignore_tables),
            })),
          },
        };
        createTicket(params)
          .then((res) => {
            ticketId.value = res.id;
            tableData.value = [getTableItem()];
            formdata.data_repair.is_repair = true;
            formdata.timing = getCurrentDate();
            formdata.runtime_hour = 48;
            nextTick(() => {
              window.changeConfirm = false;
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      })
      .catch(() => {
        isSubmitting.value = false;
      });
  }

  function handleCloseSuccess() {
    ticketId.value = 0;
  }
</script>

<style lang="less" scoped>
  .checksum {
    .checksum-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }

    .checksum-form {
      width: 360px;
      margin-top: 24px;
      margin-bottom: 32px;

      :deep(.bk-form-label) {
        font-weight: bold;
        color: @title-color;

        &::after {
          line-height: unset;
        }
      }
    }

    .repair-mode {
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

          :deep(.bk-radio-input) {
            margin-top: 2px;
          }
        }
      }
    }
  }
</style>
