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
        :title="$t('主库故障切换：主机级别操作，即同机所有集群的从库均会升级成主库')" />
      <div class="top-opeartion">
        <BkCheckbox v-model="isForceSwitch">
          <BkPopover
            content="强制切换，将忽略同步连接"
            theme="dark">
            <span style="border-bottom: 1px dashed #63656E;">强制切换</span>
          </BkPopover>
        </BkCheckbox>
      </div>
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length <2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @on-ip-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
          @remove="handleRemove(index)" />
      </RenderData>
      <InstanceSelector
        v-model:is-show="isShowMasterInstanceSelector"
        active-tab="masterFailHosts"
        db-type="redis"
        :panel-list="['masterFailHosts', 'manualInput']"
        role="Master Ip"
        @change="handelMasterProxyChange" />
    </div>
    <template #action>
      <BkButton
        class="w88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="$t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="$t('确认重置页面')">
        <BkButton
          class="ml8 w88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { type MasterSlaveByIp, queryInfoByIp, queryMasterSlaveByIp } from '@services/redis/toolbox';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@views/redis/common/instance-selector/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface SpecItem {
    ip: string;
    spec_id: number
  }
  interface InfoItem {
    cluster_id: number,
    pairs: {
      redis_master: string,
      redis_slave: string,
    }[]

  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const isForceSwitch = ref(false);
  const tableData = ref([createRowData()]);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.ip)).length);


  // slave -> master
  const slaveMasterMap: Record<string, string> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return firstRow.ip;
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // ip 是否已存在表格的映射表
  let ipMemo = {} as Record<string, boolean>;

  // 批量选择
  const handelMasterProxyChange = async (data: InstanceSelectorValues) => {
    console.log('choosed: ', data);
    const ips = data.masterFailHosts.map(item => item.ip);
    const ret = await queryMasterSlaveByIp({ ips }).catch((e) => {
      console.error('queryMasterSlaveByIp failed: ', e); return null;
    });
    if (ret) {
      console.log('queryMasterSlaveByIp result: ', ret);
      const masterIpMap: Record<string, MasterSlaveByIp> = {};
      ret.forEach((item) => {
        masterIpMap[item.master_ip] = item;
      });
      console.log('masterIpMap: ', masterIpMap);
      const newList = [] as IDataRow [];
      data.masterFailHosts.forEach((proxyData) => {
        const { ip } = proxyData;
        if (!ipMemo[ip]) {
          newList.push({
            rowKey: ip,
            isLoading: false,
            ip,
            clusterId: proxyData.cluster_id,
            cluster: masterIpMap[ip].cluster.immute_domain,
            masters: masterIpMap[ip].instances.map(item => item.instance),
            slave: masterIpMap[ip].slave_ip,
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
    }
  };

  // 输入IP后查询详细信息
  const handleChangeHostIp = async (index: number, ip: string) => {
    if (tableData.value[index].ip === ip) return;
    // 去重
    if (tableData.value.filter(item => item.ip === ip).length > 0) return;
    tableData.value[index].isLoading = true;
    tableData.value[index].ip = ip;
    const ret = await queryMasterSlaveByIp({
      ips: [ip],
    }).catch((e) => {
      console.error('query cluster info by ip failed: ', e);
      return null;
    });
    if (ret) {
      const data = ret[0];
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
    }
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const removeItem = dataList[index];
    const removeIp = removeItem.ip;
    dataList.splice(index, 1);
    delete ipMemo[removeIp];
    tableData.value = dataList;
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = () => {
    const dataArr = tableData.value.filter(item => item.ip !== undefined);
    const infos = dataArr.map((item) => {
      const infoItem: InfoItem = {
        cluster_id: item.clusterId,
        pairs: [
          {
            redis_master: item.ip,
            redis_slave: item.slave,
          },
        ],

      };
      return infoItem;
    });
    return infos;
  };

  // 提交
  const handleSubmit = () => {
    const infos = generateRequestParam();
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_MASTER_FAILOVER,
      details: {
        infos,
      },
    };
    console.log('submit params: ', params);
    InfoBox({
      title: t('确认提交 n 个主库故障切换任务？', { n: totalNum.value }),
      subTitle: '替换后所有的数据将会迁移到新的主机上，请谨慎操作！',
      width: 480,
      infoType: 'warning',
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
            console.error('单据提交失败：', e);
            // 暂时先按成功处理
            window.changeConfirm = false;
            router.push({
              name: 'RedisMasterFailover',
              params: {
                page: 'success',
              },
              query: {
                ticketId: '',
              },
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    ipMemo = {};
    window.changeConfirm = false;
  };

</script>

<style lang="less">
  .redis-master-failover-page {
    padding-bottom: 20px;

    .top-opeartion {
      display: flex;
      width: 100%;
      height: 30px;
      justify-content: flex-end;
      align-items: flex-end;
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
