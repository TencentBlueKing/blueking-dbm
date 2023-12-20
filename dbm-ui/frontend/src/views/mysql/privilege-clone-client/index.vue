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
    :steps="[{
      title: $t('单据审批'),
      status: 'loading',
    }, {
      title: $t('客户端权限克隆_执行'),
    }]"
    :ticket-id="ticketId"
    :title="$t('客户端权限克隆任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="clone-client">
    <BkAlert
      closable
      :title="$t('客户端权限克隆_访问DB来源IP替换时做的权限克隆')" />
    <BkButton
      class="clone-client-batch"
      @click="() => isShowBatchInput = true">
      <i class="db-icon-add" />
      {{ $t('批量录入') }}
    </BkButton>
    <ToolboxTable
      ref="toolboxTableRef"
      class="mb-32"
      :columns="columns"
      :data="tableData"
      :max-height="tableMaxHeight"
      @add="handleAddItem"
      @remove="handleRemoveItem" />
    <template #action>
      <AuthButton
        action-id="mysql_client_clone_rules"
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </AuthButton>
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
  <IpSelector
    v-model:show-dialog="isShowIpSelector"
    :biz-id="globalBizsStore.currentBizId"
    button-text=""
    service-mode="all"
    :show-view="false"
    @change="handleHostChange" />
</template>

<script setup lang="tsx">
  import type FormItem from 'bkui-vue/lib/form/form-item';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { precheckPermissionClone } from '@services/permission';
  import {
    checkHost,
    getHostTopoInfos,
  } from '@services/source/ipchooser';
  import { createTicket } from '@services/source/ticket';

  import { useInfo, useTableMaxHeight } from '@hooks';

  import { TicketTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import { generateId, messageError } from '@utils';

  import BatchInput from './components/BatchInput.vue';

  import SuccessView from '@/components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@/components/mysql-toolbox/ToolboxTable.vue';
  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  type FormItemInstance = InstanceType<typeof FormItem>;
  interface TableItem {
    source: string,
    target: string,
    uniqueId: string
  }
  interface TableColumnData {
    index: number,
    data: TableItem
  }

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(334);
  const getSourceInfos = (cloudIp = '') => {
    const [cloudId, ip] = cloudIp.split(':');
    return {
      cloudId,
      ip,
    };
  };

  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const isShowBatchInput = ref(false);
  const isSubmitting = ref(false);
  const isShowIpSelector = ref(false);
  const hostTopoMap: Map<string, ServiceReturnType<typeof getHostTopoInfos>['hosts_topo_info'][number]> = reactive(new Map());
  const targetHostNotExistMap: Map<string, string[]> = reactive(new Map());
  const tableData = ref<Array<TableItem>>([getTableItem()]);
  const columns: TableProps['columns'] = [
    {
      label: () => (
        <span>
          {t('源客户端IP')}
          <db-icon type="batch-host-select" onClick={() => isShowIpSelector.value = true} />
        </span>
      ),
      field: 'source',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_source`}
          error-display-type="tooltips"
          ref={setFormItemRefs.bind(null, 'source')}
          rules={getSourceRules(data)}
          property={`${index}.source`}>
          <bk-input v-model={data.source} placeholder={t('请输入xx', [t('管控区域_IP')])} />
        </bk-form-item>
      ),
    },
    {
      label: t('模块'),
      field: 'topo',
      showOverflowTooltip: false,
      render: ({ data }: TableColumnData) => {
        const topo = hostTopoMap.get(getSourceInfos(data.source).ip)?.topo || [];
        const count = topo.length;
        if (count === 0) {
          return <p class="placeholder">{t('输入客户端后自动生成')}</p>;
        }
        return (
          <div class="module-paths">
            <span class="module-paths__item text-overflow" v-overflow-tips>{topo[0]}</span>
            {
              count - 1 > 0
                ? <span class="module-paths__tag" v-bk-tooltips={{ content: topo.slice(1).join('\n') }}>+{count - 1}</span>
                : null
            }
          </div>
        );
      },
    },
    {
      label: t('新客户端IP'),
      field: 'target',
      minWidth: 230,
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_target`}
          error-display-type="tooltips"
          ref={setFormItemRefs.bind(null, 'target')}
          rules={getTargetRules(data)}
          property={`${index}.target`}>
          <db-textarea
            placeholder={t('请输入请输入IP_多个IP用换行分隔')}
            display-height={42}
            v-model={data.target}
            max-height={100}
            row-height={28}
          />
        </bk-form-item>
      ),
    },
  ];
  // 设置 target|source form-item
  const formItemRefs = reactive({
    target: [] as FormItemInstance[],
    source: [] as FormItemInstance[],
  });
  function setFormItemRefs(key: 'target' | 'source', vueInstance: FormItemInstance) {
    if (vueInstance) {
      const refs = formItemRefs[key];
      const refProperties = refs.map(item => item.$props.property);
      const curProperty = vueInstance.$props.property;
      if (!refProperties.includes(curProperty)) {
        formItemRefs[key].push(vueInstance);
      }
    }
  }

  /**
   * 获取表格数据
   */
  function getTableItem(): TableItem {
    return {
      // topo: [],
      source: '',
      target: '',
      uniqueId: generateId('CLONE_CLIENT_'),
    };
  }

  /**
   * 获取源客户端 ip 正则校验
   */
  function getSourceRules(data: TableItem) {
    return [
      {
        validator: (ip: string) => !!ip,
        message: t('请输入'),
        trigger: 'blur',
      },
      {
        validator: (ip: string) => {
          const items = ip.split(':');
          return items.length === 2 && /^\d+$/.test(items[0]);
        },
        message: t('请输入xx', [t('管控区域')]),
        trigger: 'blur',
      },
      {
        validator: (ip: string) => {
          const items = ip.split(':');
          return ipv4.test(items[1]);
        },
        message: t('请输入合法ipv4'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => verifySourceHost(data, value),
        message: t('IP不存在'),
        trigger: 'blur',
      },
    ];
  }

  /**
   * 获取新客户端 ip 正则校验
   */
  function getTargetRules(data: TableItem) {
    return [
      {
        validator: (val: string) => {
          const targets = val.split('\n').map(ip => ip.trim());
          return targets.every(ip => ipv4.test(ip));
        },
        message: t('请输入合法ipv4'),
        trigger: 'blur',
      },
      {
        validator: (val: string) => {
          const targets = val.split('\n').map(ip => ip.trim());
          return targets.every(ip => ip !== getSourceInfos(data.source).ip);
        },
        message: t('xx为源客户端IP', [getSourceInfos(data.source).ip]),
        trigger: 'blur',
      },
      {
        validator: (val: string) => {
          const targets = val.split('\n').map(ip => ip.trim());
          const uniqueTargets = _.uniq(targets);
          return targets.length === uniqueTargets.length;
        },
        message: t('新客户端IP重复'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => verifyTargetHost(data, value),
        message: () => `${targetHostNotExistMap.get(data.uniqueId)?.join('，')} ${t('IP不存在')}`,
        trigger: 'blur',
      },
    ];
  }

  /**
   * 查询主机拓扑
   */
  function fetchHostTopoInfos(ips: string[]) {
    return getHostTopoInfos({
      bk_biz_id: globalBizsStore.currentBizId,
      filter_conditions: {
        bk_host_innerip: ips,
      },
    }).then((res) => {
      for (const item of res.hosts_topo_info) {
        hostTopoMap.set(item.ip, item);
      }
      return res;
    });
  }

  /**
   * 校验源客户端主机是否存在
   */
  function verifySourceHost(data: TableItem, value: string) {
    // 已经查询过且存在的主机
    const curHostTopo = hostTopoMap.get(getSourceInfos(data.source).ip)?.topo || [];
    if (curHostTopo.length > 0) {
      return true;
    }

    const ips = tableData.value.map(item => item.source).filter(source => ipv4.test(getSourceInfos(source).ip.trim()));
    return fetchHostTopoInfos(ips).then(() => Boolean(hostTopoMap.get(getSourceInfos(value).ip)?.topo?.length));
  }

  /**
   * 校验新客户端主机是否存在
   */
  function verifyTargetHost(data: TableItem, value: string) {
    const targets = value.split('\n')
      .map(ip => ip.trim())
      .filter(ip => ip);
    targetHostNotExistMap.delete(data.uniqueId);

    // 已经查询过且存在的主机
    if (targets.every(ip => Boolean(hostTopoMap.get(ip)?.topo?.length))) {
      return true;
    }

    return fetchHostTopoInfos(targets).then((res) => {
      // 判断主机是否存在
      const existHosts = res.hosts_topo_info.filter(item => item.topo.length !== 0).map(item => item.ip);
      const hasNotExistHost = existHosts.length !== targets.length;
      if (hasNotExistHost) {
        const notExistHosts = targets.filter(ip => !existHosts.includes(ip));
        targetHostNotExistMap.set(data.uniqueId, notExistHosts);
      }
      return !hasNotExistHost;
    });
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
  async function handleBatchInput(list: Array<{ source: string, target: string }>) {
    const formatList = list.map(item => ({
      ...getTableItem(),
      source: item.source,
      target: item.target,
    }));
    clearEmptyTableData();
    tableData.value.push(...formatList);
    window.changeConfirm = true;

    const hosts = list.reduce((hosts: string[], item) => hosts.concat([item.source, ...item.target.split('\n')]), []);

    try {
      await Promise.all([fetchHostTopoInfos(hosts)]);
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
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }

  async function handleHostChange(data: ServiceReturnType<typeof checkHost>) {
    const newList = data.map(item => ({
      ...getTableItem(),
      source: `${item.cloud_id}:${item.ip}`,
    }));

    clearEmptyTableData();
    tableData.value.push(...newList);
    window.changeConfirm = true;

    try {
      await fetchHostTopoInfos(newList.map(item => item.source));
    } catch (e) {
      console.log(e);
    }
  }

  function handleSubmit() {
    toolboxTableRef.value.validate()
      .then(() => {
        isSubmitting.value = true;
        precheckPermissionClone({
          bizId: globalBizsStore.currentBizId,
          clone_type: 'client',
          clone_cluster_type: 'mysql',
          clone_list: tableData.value.map((item) => {
            const sourceInfos = getSourceInfos(item.source);
            return {
              source: sourceInfos.ip,
              target: item.target,
              bk_cloud_id: sourceInfos.cloudId,
              module: hostTopoMap.get(sourceInfos.ip)?.topo?.[0] || '',
            };
          }),
        })
          .then((res) => {
            if (res.pre_check) {
              createTicket({
                ticket_type: TicketTypes.MYSQL_CLIENT_CLONE_RULES,
                bk_biz_id: globalBizsStore.currentBizId,
                details: {
                  ...res,
                  clone_type: 'client',
                },
              })
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
              return;
            }
            isSubmitting.value = false;
            messageError(res.message);
          })
          .catch(() => {
            isSubmitting.value = false;
          });
      });
  }

  function handleCloseSuccess() {
    ticketId.value = 0;
  }
</script>

<style lang="less" scoped>
  .clone-client {
    height: calc(100% - 20px);
    overflow: hidden;

    .clone-client-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }

    :deep(.mysql-toolbox-table) {
      .module-paths {
        display: flex;
        align-items: center;
        padding: 0 12px;
        background-color: white;

        .module-paths__item {
          flex: 1;
        }

        .module-paths__tag {
          padding: 0 6px;
          line-height: 18px;
          color: @gray-color;
          background-color: #f0f1f5;
          flex-shrink: 0;
        }
      }
    }
  }
</style>
