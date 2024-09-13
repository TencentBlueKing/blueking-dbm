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
    <RenderData
      class="mt16"
      @batch-select-cluster="handleShowInstanceSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderData>
    <div class="safe-action">
      <BkCheckbox
        v-model="isSafe"
        v-bk-tooltips="t('如忽略_在有连接的情况下Proxy也会执行替换')"
        :false-label="1"
        :true-label="0">
        <span class="safe-action-text">{{ t('忽略业务连接') }}</span>
      </BkCheckbox>
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
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <InstanceSelector
      v-model:is-show="isShowInstanceSelecotr"
      :cluster-types="[TENDBHA_HOST]"
      :selected="selectedIntances"
      :tab-list-config="tabListConfig"
      @change="handelProxySelectorChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaMachine from '@services/model/mysql/tendbha-machine';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  import { messageError } from '@utils';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type IHostData } from './components/RenderData/Row.vue';

  interface InfoItem {
    cluster_ids: string[];
    origin_proxy: IHostData;
    target_proxy: IHostData;
  }

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_PROXY_SWITCH,
    onSuccess(cloneData) {
      const { force, tableDataList } = cloneData;
      tableData.value = tableDataList;
      isSafe.value = force ? 1 : 0;
      window.changeConfirm = true;
    },
  });
  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const TENDBHA_HOST = 'TendbhaHost';
  const tabListConfig = {
    [TENDBHA_HOST]: [
      {
        id: [TENDBHA_HOST],
        name: t('目标Proxy主机'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 主机'),
            field: 'ip',
            role: 'proxy',
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 主机'),
            field: 'ip',
            role: 'proxy',
          },
        },
      },
    ],
  } as unknown as Record<string, PanelListType>;
  // 实例是否已存在表格的映射表
  let ipMemo: Record<string, boolean> = {};

  const isShowInstanceSelecotr = ref(false);
  const rowRefs = ref([] as InstanceType<typeof RenderDataRow>[]);
  const isSafe = ref(1);
  const isSubmitting = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIntances = shallowRef<InstanceSelectorValues<TendbhaMachine>>({ [TENDBHA_HOST]: [] });

  const handleShowInstanceSelector = () => {
    isShowInstanceSelecotr.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.originProxy?.ip;
  };

  // 批量选择
  const handelProxySelectorChange = (data: InstanceSelectorValues<TendbhaMachine>) => {
    selectedIntances.value = data;
    const newList = data[TENDBHA_HOST].reduce((results, item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        const row = createRowData({
          originProxy: {
            ip,
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            bk_biz_id: currentBizId,
            port: item.related_instances[0].port,
          },
          relatedInstances: (item.related_instances as unknown as IDataRow['relatedInstances'])?.map((item) => ({
            cluster_id: item.cluster_id,
            instance: item.instance,
          })),
        });
        results.push(row);
        ipMemo[ip] = true;
      }
      return results;
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

    // 多行输入，新增行需要触发校验取到源Proxy信息后下发给目标Proxy
    setTimeout(() => {
      for (let i = index + 1; i <= appendList.length + index; i++) {
        rowRefs.value[i].getValue();
      }
    });
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const ip = tableData.value[index].originProxy?.ip;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selectedIntances.value[TENDBHA_HOST];
      selectedIntances.value[TENDBHA_HOST] = clustersArr.filter((item) => item.ip !== ip);
    }
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue())).then(
      (params: InfoItem[]) => {
        const targetIpMap: Record<string, string[]> = {};
        const infos: InfoItem[] = [];
        const sourceIpMap: Record<string, InfoItem> = {};
        let isMultipleSourceToSingleTarget = false;
        for (const rowInfo of params) {
          const targetProxyIp = rowInfo.target_proxy.ip;
          const originProxyIp = rowInfo.origin_proxy.ip;
          if (!sourceIpMap[originProxyIp]) {
            sourceIpMap[originProxyIp] = rowInfo;
            infos.push(rowInfo);
          } else {
            // 多个同IP不同Port的源Proxy与同一个目标Proxy IP进行合并
            if (sourceIpMap[originProxyIp].target_proxy.ip !== targetProxyIp) {
              infos.push(rowInfo);
            } else {
              // 集群ID去重合并
              const targetInfo = infos.find((item) => item.origin_proxy.ip === originProxyIp)!;
              const newClusterIds = Array.from(new Set([...targetInfo.cluster_ids, ...rowInfo.cluster_ids]));
              targetInfo.cluster_ids = newClusterIds;
            }
          }
          if (!targetIpMap[targetProxyIp]) {
            targetIpMap[targetProxyIp] = [originProxyIp];
          } else {
            if (!targetIpMap[targetProxyIp].includes(originProxyIp)) {
              isMultipleSourceToSingleTarget = true;
              targetIpMap[targetProxyIp].push(originProxyIp);
            }
          }
        }
        // 多个不同的源IP对应同一个目标IP，不允许提单
        if (isMultipleSourceToSingleTarget) {
          let tipStr = '';
          Object.entries(targetIpMap).forEach(([targetIp, sourceIpList]) => {
            if (sourceIpList.length > 1) {
              tipStr += `[${sourceIpList.join(',')}] -> ${targetIp}`;
            }
          });
          messageError(t('不允许多台目标Proxy主机对应同一台新Proxy主机：x', { x: tipStr }), 5000);
          isSubmitting.value = false;
          return;
        }

        createTicket({
          ticket_type: 'MYSQL_PROXY_SWITCH',
          remark: '',
          details: {
            infos,
            is_safe: Boolean(isSafe.value),
          },
          bk_biz_id: currentBizId,
        })
          .then((data) => {
            window.changeConfirm = false;

            router.push({
              name: 'MySQLProxyReplace',
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
    );
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    ipMemo = {};
    selectedIntances.value[TENDBHA_HOST] = [];
    window.changeConfirm = false;
  };
</script>
