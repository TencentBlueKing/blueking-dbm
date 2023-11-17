<!-- eslint-disable max-len -->
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
        :title="t('主从切换：针对TendisSSD、TendisCache，主从切换是把Slave提升为Master，原Master被剔除，针对Tendisplus集群，主从切换是把Slave和Master互换')" />
      <BkLoading :loading="isLoading">
        <RenderData
          class="mt16"
          @show-master-batch-selector="handleShowMasterBatchSelector">
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :inputed-ips="inputedIps"
            :removeable="tableData.length <2"
            @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
            @on-ip-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { queryMasterSlaveByIp } from '@services/source/redisToolbox';
  import { createTicket } from '@services/source/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@components/instance-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';

  type MasterSlaveByIp = ServiceReturnType<typeof queryMasterSlaveByIp>[number];

  interface ChoosedFailedMasterItem {
    cluster_id: number;
    ip: string;
    role?: string;
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const isForceSwitch = ref(false);
  const tableData = ref([createRowData()]);
  const isLoading = ref(false);

  const selected = shallowRef({ redis: [] } as InstanceSelectorValues<ChoosedFailedMasterItem>);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.ip)).length);
  const inputedIps = computed(() => tableData.value.map(item => item.ip));

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

  // 批量选择
  const handelMasterProxyChange = async (data: InstanceSelectorValues) => {
    selected.value = data;
    const ips = data.redis.map(item => item.ip);
    isLoading.value = true;
    const ret = await queryMasterSlaveByIp({ ips }).finally(() => {
      isLoading.value  = false;
    });
    const masterIpMap: Record<string, MasterSlaveByIp> = {};
    ret.forEach((item) => {
      masterIpMap[item.master_ip] = item;
    });
    const newList = [] as IDataRow [];
    data.redis.forEach((proxyData) => {
      const { ip } = proxyData;
      if (!ipMemo[ip]) {
        newList.push({
          rowKey: ip,
          isLoading: false,
          ip,
          clusterId: proxyData.cluster_id,
          cluster: masterIpMap[ip]?.cluster?.immute_domain,
          masters: masterIpMap[ip]?.instances.map(item => item.instance),
          slave: masterIpMap[ip]?.slave_ip,
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
  const handleChangeHostIp = async (index: number, ip: string) => {
    if (!ip) {
      const { ip } = tableData.value[index];
      ipMemo[ip] = false;
      tableData.value[index].ip = '';
      return;
    }
    tableData.value[index].isLoading = true;
    tableData.value[index].ip = ip;
    const ret = await queryMasterSlaveByIp({
      ips: [ip],
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (ret.length === 0) {
      return;
    }
    const data = ret[0];
    if (data.instances.filter(item => item.status !== 'running').length > 0) {
      const obj = {
        rowKey: tableData.value[index].rowKey,
        isLoading: false,
        ip,
        clusterId: data.cluster.id,
        cluster: data.cluster?.immute_domain,
        masters: data.instances.map(item => item.instance),
        slave: data.slave_ip,
      };
      tableData.value[index] = obj;
      ipMemo[ip]  = true;
      selected.value.redis.push(Object.assign(data, {
        cluster_id: obj.clusterId,
        ip,
      }));
    } else {
      tableData.value[index].ip = '';
    }
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
    selected.value.redis = arr.filter(item => item.ip !== removeIp);
  };

  // 提交
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));

    const params: SubmitTicket<TicketTypes, InfoItem[]> & { details: { force: boolean }} = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
      details: {
        force: isForceSwitch.value,
        infos,
      },
    };
    InfoBox({
      title: t('确认提交 n 个主从切换任务？', { n: totalNum.value }),
      subTitle: t('从库将会直接替换主库所有信息，请谨慎操作！'),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
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
        })
          .catch((e) => {
            // 目前后台还未调通
            console.error('master failover submit ticket error', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
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
          border-bottom: 1px dashed #63656E;
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
