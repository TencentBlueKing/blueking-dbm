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
    <div class="redis-master-failover-page">
      <BkAlert
        closable
        theme="info"
        :title="title" />
      <BkLoading :loading="isLoading">
        <RenderData
          class="mt16"
          @batch-edit-backup-local="handleBatchEditBackupLocal"
          @show-master-batch-selector="handleShowMasterBatchSelector">
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :inputed-ips="inputedIps"
            :removeable="tableData.length < 2"
            @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
            @clone="(payload: IDataRow) => handleClone(index, payload)"
            @on-ip-input-finish="(ipInfo: string) => handleChangeHostIp(index, ipInfo)"
            @remove="handleRemove(index)" />
        </RenderData>
      </BkLoading>
      <div class="bottom-opeartion">
        <BkPopover
          :content="t('强制切换，将忽略同步连接')"
          placement="top"
          theme="dark">
          <div class="switch-box">
            <BkCheckbox v-model="isForceSwitch" />
            <span class="ml-6 force-switch">{{ t('强制切换') }}</span>
          </div>
        </BkPopover>
      </div>
      <TicketRemark v-model="remark" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
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
    <InstanceSelector
      v-model:is-show="isShowMasterInstanceSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selected"
      @change="handelMasterProxyChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { queryMachineInstancePair } from '@services/source/redisToolbox';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, { type InstanceSelectorValues } from '@components/instance-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  interface ChoosedFailedMasterItem {
    bk_cloud_id: number;
    cluster_id: number;
    ip: string;
    role?: string;
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
    onSuccess(cloneData) {
      const { tableList, force } = cloneData;

      tableData.value = tableList;
      isForceSwitch.value = force;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const isForceSwitch = ref(false);
  const tableData = ref([createRowData()]);
  const isLoading = ref(false);
  const remark = ref('');

  const selected = shallowRef({ redis: [] } as InstanceSelectorValues<ChoosedFailedMasterItem>);

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.ip)).length);
  const inputedIps = computed(() => tableData.value.map((item) => item.ip));

  const title = t(
    '主从切换：针对TendisSSD、TendisCache，主从切换是把Slave提升为Master，原Master被剔除，针对Tendisplus集群，主从切换是把Slave和Master互换',
  );
  // ip 是否已存在表格的映射表
  let ipMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.ip;
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  const handleBatchEditBackupLocal = (value: string) => {
    if (!value || checkListEmpty(tableData.value)) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, {
        switchMode: value,
      });
    });
  };

  // 批量选择
  const handelMasterProxyChange = async (data: InstanceSelectorValues<ChoosedFailedMasterItem>) => {
    selected.value = data;
    const ips = data.redis.map((item) => `${item.bk_cloud_id}:${item.ip}`);
    isLoading.value = true;
    const pairResult = await queryMachineInstancePair({ machines: ips }).finally(() => {
      isLoading.value = false;
    });
    const masterIpMap = pairResult.machines!;

    const newList = [] as IDataRow[];
    data.redis.forEach((proxyData) => {
      const { ip } = proxyData;
      const key = `${proxyData.bk_cloud_id}:${ip}`;
      if (!ipMemo[ip]) {
        newList.push({
          rowKey: ip,
          isLoading: false,
          ip,
          clusterIds: masterIpMap[key].related_clusters.map((item) => item.id),
          clusters: masterIpMap[key].related_clusters.map((item) => item.immute_domain),
          masters: masterIpMap[key].related_pair_instances.map((item) => item.instance),
          slave: masterIpMap[key].ip,
        });
        ipMemo[ip] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入IP后查询详细信息
  const handleChangeHostIp = async (index: number, ipInfo: string) => {
    const ipInfos = ipInfo.split(':');
    const ip = ipInfos[1];
    if (ip === tableData.value[index].ip) {
      return;
    }
    if (!ip) {
      const { ip } = tableData.value[index];
      ipMemo[ip] = false;
      tableData.value[index].ip = '';
      return;
    }
    tableData.value[index].isLoading = true;
    tableData.value[index].ip = ip;
    const pairResult = await queryMachineInstancePair({ machines: [ipInfo] }).finally(() => {
      tableData.value[index].isLoading = false;
    });

    const masterIpMap = pairResult.machines!;
    if (!masterIpMap[ipInfo]) {
      return;
    }
    const data = masterIpMap[ipInfo];
    // if (data.instances.filter(item => item.status !== 'running').length > 0) {
    const obj = {
      rowKey: tableData.value[index].rowKey,
      isLoading: false,
      ip,
      clusterIds: data.related_clusters.map((item) => item.id),
      clusters: data.related_clusters.map((item) => item.immute_domain),
      masters: data.related_pair_instances.map((item) => item.instance),
      slave: data.ip,
    };
    tableData.value[index] = obj;
    ipMemo[ip] = true;
    // selected.value.redis.push(
    //   Object.assign(data, {
    //     cluster_id: obj.clusterIds[0],
    //     ip,
    //   }),
    // );
    // } else {
    //   tableData.value[index].ip = '';
    // }
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const removeIp = removeItem.ip;
    tableData.value.splice(index, 1);
    delete ipMemo[removeIp];
    const arr = selected.value.redis;
    selected.value.redis = arr.filter((item) => item.ip !== removeIp);
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, sourceData);
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  // 提交
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(
        rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue()),
      );
      const params = {
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
        remark: remark.value,
        details: {
          force: isForceSwitch.value,
          infos,
        },
      };
      await createTicket(params).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'RedisMasterFailover',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = '';
    selected.value.redis = [];
    ipMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .redis-master-failover-page {
    padding-bottom: 20px;

    .bottom-opeartion {
      display: flex;
      width: 100%;
      height: 30px;
      align-items: flex-end;

      .switch-box {
        display: flex;
        align-items: center;

        .force-switch {
          font-size: 12px;
          border-bottom: 1px dashed #63656e;
        }
      }
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
