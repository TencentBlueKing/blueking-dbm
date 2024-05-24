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
        title: t('添加从库_执行'),
      },
    ]"
    :ticket-id="ticketId"
    :title="t('添加从库任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="slave-add">
    <div class="pb-20">
      <BkAlert
        closable
        :title="t('添加从库_同机的所有集群会统一新增从库_但新机器不添加到域名解析中去')" />
      <BkButton
        class="slave-add-batch"
        @click="() => (isShowBatchInput = true)">
        <i class="db-icon-add" />
        {{ t('批量录入') }}
      </BkButton>
      <ToolboxTable
        ref="toolboxTableRef"
        class="mb-32"
        :columns="columns"
        :data="tableData"
        :max-height="tableMaxHeight"
        @add="handleAddItem"
        @clone="handleCloneItem"
        @remove="handleRemoveItem" />
      <BkForm
        class="toolbox-form mb-20"
        form-type="vertical">
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
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
    @change="handleBatchSelectorChange" />
</template>

<script setup lang="tsx">
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { checkHost } from '@services/source/ipchooser';
  import {
    findRelatedClustersByClusterIds,
    getClusterInfoByDomains,
  } from '@services/source/mysqlCluster';
  import { createTicket } from '@services/source/ticket';

  import { useTableMaxHeight, useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import SuccessView from '@components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@components/mysql-toolbox/ToolboxTable.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import { generateId } from '@utils';

  import type { TableColumnData, TableItem } from './common/types';
  import BatchInput from './components/BatchInput.vue';
  import ClusterRelatedInput from './components/ClusterRelatedInput.vue';

  import type { TableProps } from '@/types/bkui-vue';

  /**
   * 获取表格数据
   */
  const getTableItem = (): TableItem => ({
    cluster_domain: '',
    cluster_id: 0,
    cluster_related: [],
    checked_related: [],
    new_slave_ip: '',
    uniqueId: generateId('SLAVE_ADD_'),
  });

  const {
    t,
    locale,
  } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(334);

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_ADD_SLAVE,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      remark.value = cloneData.remark;
      fetchClusterInfoByDomains();
      window.changeConfirm = true;
    },
  });

  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const clusterInfoMap: Map<string, TendbhaModel> = reactive(new Map());
  const hostInfoMap: Map<string, ServiceReturnType<typeof checkHost>[number]> = reactive(new Map());
  const tableData = ref<Array<TableItem>>([getTableItem()]);
  const backupSource = ref('local');
  const remark = ref('')

  const selectedClusters = shallowRef<{[key: string]: Array<TendbhaModel>}>({ [ClusterTypes.TENDBHA]: [] });

  const isCN = computed(() => locale.value === 'zh-cn');

  const columns: TableProps['columns'] = [
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
          rules={getRules(data).cluster}
          property={`${index}.cluster_domain`}>
          <ClusterRelatedInput
            data={data}
            v-model={[data.cluster_domain, ['trim']]}
            placeholder={t('请输入集群域名')}
            onBlur={hanldeDomainBlur.bind(null, index)}
            onChange-related={(value: number[]) => handleChangeRelated(index, value)}
          />
        </bk-form-item>
      ),
    },
    {
      label: t('新从库主机'),
      field: 'new_slave_ip',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_new_slave_ip`}
          error-display-type="tooltips"
          rules={getRules(data).slave}
          property={`${index}.new_slave_ip`}>
          <bk-input
            v-model={[data.new_slave_ip, ['trim']]}
            placeholder={t('请输入单个IP')} />
        </bk-form-item>
      ),
    },
  ];

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const getHostInfo = (domain: string, ip: string) => {
    const clusterInfo = clusterInfoMap.get(domain);
    return hostInfoMap.get(`${clusterInfo?.bk_cloud_id}:${ip}`);
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<TableItem>) => {
    if (list.length > 1) {
      return false;
    }

    const [firstRow] = list;
    return !firstRow?.cluster_domain;
  };

  const getRules = (data: TableItem) => {
    const bizName = isCN.value ? globalBizsStore.currentBizInfo?.name || '--' : globalBizsStore.currentBizInfo?.english_name || '--';
    return {
      cluster: [
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
      ],
      slave: [
        {
          validator: (value: string) => ipv4.test(value),
          message: t('请输入合法IP'),
          trigger: 'blur',
        },
        {
          validator: (value: string) => {
            // 还未填写目标集群暂时先跳过改校验
            if (!data.cluster_id) return true;

            return verifyIP(data, value);
          },
          message: t('IP不在x业务空闲机模块', { name: bizName }),
          trigger: 'blur',
        },
        {
          validator: () => {
            // 还未填写目标集群暂时先跳过改校验
            if (!data.cluster_id) return true;

            const hostInfo = getHostInfo(data.cluster_domain, data.new_slave_ip);
            if (hostInfo) {
              return true;
            }

            return false;
          },
          message: t('新主机xx跟目标集群xx须在同一个管控区域', {
            ip: data.new_slave_ip,
            cluster: data.cluster_domain,
          }),
          trigger: 'blur',
        },
      ],
    };
  };

  /**
   * 设置集群 id
   */
  const hanldeDomainBlur = (index: number) => {
    const item = tableData.value[index];
    const info = clusterInfoMap.get(item.cluster_domain);
    if (item.cluster_id !== info?.id) {
      item.cluster_id = info?.id ?? 0;
      item.cluster_related = [];
      item.checked_related = [];
    }
  };

  /**
   * 切换关联集群选中
   */
  const handleChangeRelated = (index: number, values: number[]) => {
    const item = tableData.value[index];
    item.checked_related = item.cluster_related.filter(item => values.includes(item.id));
  };


  /**
   * 校验主机是否存在
   */
  const verifyIP = (data: TableItem, value: string) => {
    if (getHostInfo(data.cluster_domain, value) !== undefined) {
      return true;
    }

    return fetchHosts().then(() => getHostInfo(data.cluster_domain, value) !== undefined);
  };

  /**
   * 根据集群域名获取集群信息
   */
  const fetchHosts = () => {
    const ips = tableData.value
      .filter(item => (
        item.new_slave_ip && getHostInfo(item.cluster_domain, item.new_slave_ip) === undefined
      )) // 过滤掉已经获取的主机
      .map(item => item.new_slave_ip);

    const params = {
      scope_list: [
        {
          scope_id: globalBizsStore.currentBizId,
          scope_type: 'biz',
        },
      ],
      ip_list: ips,
      mode: 'idle_only',
    };

    return checkHost(params)
      .then((res) => {
        for (const item of res) {
          hostInfoMap.set(`${item.cloud_id}:${item.ip}`, item);
        }
        return res;
      });
  };

  /**
   * 校验集群域名是否存在
   */
  const verifyCluster = (value: string) => {
    const clusterInfo = clusterInfoMap.get(value);
    if (clusterInfo?.master_domain) {
      fetchRelatedClusters([clusterInfo.id]);
      return true;
    }

    return fetchClusterInfoByDomains().then(() => {
      const clusterId = clusterInfoMap.get(value)?.id;
      clusterId && fetchRelatedClusters([clusterId]);
      return Boolean(clusterId);
    });
  };

  /**
   * 根据集群域名获取集群信息
   */
  const fetchClusterInfoByDomains = () => {
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
          }
        }

        return res;
      });
  };

  /**
   * 获取同机关联集群
   */
  const fetchRelatedClusters = (clusterIds: number[]) => findRelatedClustersByClusterIds({
    bk_biz_id: globalBizsStore.currentBizId,
    cluster_ids: clusterIds,
  }).then((res) => {
    for (const item of res) {
      const tableItems = tableData.value.filter(tableItem => tableItem.cluster_id === item.cluster_id);
      for (const tableItem of tableItems) {
        tableItem.cluster_related = item.related_clusters;
        tableItem.checked_related = item.related_clusters;
      }
    }
  });

  /**
   * 集群选择器批量选择
   */
  const handleBatchSelectorChange = (selected: Record<string, Array<TendbhaModel>>) => {
    selectedClusters.value = selected;
    const formatList: TableItem[] = [];
    selected[ClusterTypes.TENDBHA].forEach((item) => {
      const domain = item.master_domain;
      clusterInfoMap.set(domain, item);
      if (!domainMemo[domain]) {
        const row = {
          ...getTableItem(),
          cluster_domain: domain,
          cluster_id: item.id,
        };
        formatList.push(row);
        domainMemo[domain] = true;
      }
    });

    clearEmptyTableData();
    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
    fetchRelatedClusters(formatList.map(item => item.cluster_id));
  };

  /**
   * 批量添加若只有一行且为空则清空
   */
  const clearEmptyTableData = () => {
    if (tableData.value.length === 1) {
      const data = tableData.value[0];
      if (Object.values({ ...data, uniqueId: '' }).every(value => (Array.isArray(value) ? !value.length : !value))) {
        tableData.value = [];
      }
    }
  };

  /**
   * 批量录入
   */
  const handleBatchInput = async (list: Array<{ cluster: string, ip: string }>) => {
    const formatList = list.map(item => ({
      ...getTableItem(),
      cluster_domain: item.cluster,
      new_slave_ip: item.ip,
    }));
    clearEmptyTableData();
    tableData.value.push(...formatList);
    window.changeConfirm = true;

    try {
      await Promise.all([fetchHosts, fetchClusterInfoByDomains]);
    } catch (e) {
      console.log(e);
    }

    // 触发表格校验
    toolboxTableRef.value.validate();
  };

  const handleAddItem = (index: number) => {
    tableData.value.splice(index + 1, 0, getTableItem());
  };

  const handleRemoveItem = (index: number) => {
    const dataList = [...tableData.value];
    const domain = dataList[index].cluster_domain;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
      selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter(item => item.master_domain !== domain);
    }
    tableData.value.splice(index, 1);
  };

  const handleCloneItem = (index: number) => {
    tableData.value.splice(index + 1, 0, _.cloneDeep(tableData.value[index]));
    setTimeout(() => {
      toolboxTableRef.value.validate();
    })
  }

  const handleReset = () => {
    InfoBox({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      cancelText : t('取消'),
      onConfirm: () => {
        tableData.value = [getTableItem()];
        remark.value = ''
        selectedClusters.value[ClusterTypes.TENDBHA] = [];
        domainMemo = {};
        window.changeConfirm = false;
        return true;
      },
    });
  };

  const handleSubmit = () => {
    toolboxTableRef.value.validate()
      .then(() => {
        isSubmitting.value = true;
        const params = {
          ticket_type: TicketTypes.MYSQL_ADD_SLAVE,
          bk_biz_id: globalBizsStore.currentBizId,
          remark: remark.value,
          details: {
            infos: tableData.value.map((item) => {
              const hostInfo = getHostInfo(item.cluster_domain, item.new_slave_ip);

              return {
                new_slave: {
                  bk_biz_id: hostInfo?.biz?.id,
                  bk_cloud_id: hostInfo?.cloud_id,
                  bk_host_id: hostInfo?.host_id,
                  ip: item.new_slave_ip,
                },
                cluster_ids: [item.cluster_id].concat(item.checked_related.map(item => item.id)),
              };
            }),
            backup_source: backupSource.value,
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
  };

  const handleCloseSuccess = () => {
    ticketId.value = 0;
  };
</script>

<style lang="less" scoped>
  .slave-add {
    height: 100%;
    overflow: hidden;

    .slave-add-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }
  }
</style>
