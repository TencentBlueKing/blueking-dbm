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
    <div class="proxy-scale-down-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('集群分片变更：xxx')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @click-select="() => handleClickSelect(index)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div
        class="title-spot"
        style="margin: 22px 0 12px;">
        校验与修复类型<span class="required" />
      </div>
      <BkRadioGroup
        v-model="repairAndVerifyType">
        <BkRadio
          v-for="item in repairAndVerifyTypeList"
          :key="item.value"
          :label="item.value">
          {{ item.label }}
        </BkRadio>
      </BkRadioGroup>
    </div>
    <template #action>
      <BkButton
        class="w-88"
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :tab-list="clusterSelectorTabList"
      @change="handelClusterChange" />
    <ChooseClusterTargetPlan
      v-model:is-show="showChooseClusterTargetPlan"
      :data="activeRowData"
      @click-cancel="() => showChooseClusterTargetPlan = false"
      @click-confirm="handleChoosedTargetCapacity" />
  </SmartAction>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisModel, { RedisClusterTypes } from '@services/model/redis/redis';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ChooseClusterTargetPlan, { type Props as TargetPlanProps } from '@views/redis/common/cluster-deploy-plan/Index.vue';
  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';
  import { getClusterInfo } from '@views/redis/common/utils';

  import RenderData from './components/Index.vue';
  import { OnlineSwitchType } from './components/RenderSwitchMode.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface GetRowMoreInfo {
    targetNum: number;
    switchMode: OnlineSwitchType;
  }

  interface InfoItem {
    cluster_id: number,
    bk_cloud_id: number,
    target_proxy_count:number,
    online_switch_type: OnlineSwitchType,
  }


  enum RepairAndVerifyModes {
    DATA_CHECK_AND_REPAIR = 'data_check_and_repair', // 数据校验并修复
    DATA_CHECK_ONLY = 'data_check_only', // 仅进行数据校验，不进行修复
    NO_CHECK_NO_REPAIR = 'no_check_no_repair', // 不校验不修复
  }

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const rowRefs = ref();
  const isShowClusterSelector = ref(false);
  const isSubmitting  = ref(false);
  const showChooseClusterTargetPlan = ref(false);
  const activeRowData = ref<TargetPlanProps['data']>();
  const activeRowIndex = ref(0);
  const repairAndVerifyType = ref(RepairAndVerifyModes.DATA_CHECK_AND_REPAIR);

  const tableData = ref([createRowData()]);
  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.srcCluster)).length);

  const clusterSelectorTabList = [ClusterTypes.REDIS];


  const repairAndVerifyTypeList = [
    {
      label: '校验并修复',
      value: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
    },
    {
      label: '只校验，不修复',
      value: RepairAndVerifyModes.DATA_CHECK_ONLY,
    },
    {
      label: '不校验，不修复',
      value: RepairAndVerifyModes.NO_CHECK_NO_REPAIR,
    },
  ];

  // 集群域名是否已存在表格的映射表
  let domainMemo:Record<string, boolean> = {};

  // 点击部署方案
  const handleClickSelect = (index: number) => {
    activeRowIndex.value = index;
    const rowData = tableData.value[index];
    if (rowData.srcCluster) {
      const obj = {
        targetCluster: rowData.srcCluster,
        currentSepc: '',
        capacity: { total: 1, used: 0 },
        clusterType: RedisClusterTypes.TwemproxyRedisInstance,
        shardNum: 0,
      };
      activeRowData.value = obj;
      showChooseClusterTargetPlan.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = () => {
    showChooseClusterTargetPlan.value = false;
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow[] = [];
    const domains = list.map(item => item.immute_domain);
    const clustersInfo = await getClusterInfo(domains);
    // 根据映射关系匹配
    clustersInfo.forEach((item) => {
      const domain = item.cluster.immute_domain;
      if (!domainMemo[domain]) {
        const row = {
          rowKey: item.cluster.immute_domain,
          isLoading: false,
          srcCluster: item.cluster.immute_domain,
          clusterId: item.cluster.id,
          bkCloudId: item.cluster.bk_cloud_id,
          switchMode: OnlineSwitchType.USER_CONFIRM,
        };
        newList.push(row);
        domainMemo[domain] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    const ret = await getClusterInfo(domain);
    const data = ret[0];
    const row = {
      rowKey: data.cluster.immute_domain,
      isLoading: false,
      srcCluster: data.cluster.immute_domain,
      clusterId: data.cluster.id,
      bkCloudId: data.cluster.bk_cloud_id,
      switchMode: OnlineSwitchType.USER_CONFIRM,
    };
    tableData.value[index] = row;
    domainMemo[domain] = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const { srcCluster } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster];
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (moreList: GetRowMoreInfo[]) => {
    const infos = tableData.value.reduce((result: InfoItem[], item, index) => {
      if (item.srcCluster) {
        const obj: InfoItem = {
          cluster_id: item.clusterId,
          bk_cloud_id: item.bkCloudId,
          target_proxy_count: moreList[index].targetNum,
          online_switch_type: moreList[index].switchMode,
        };
        result.push(obj);
      }
      return result;
    }, []);
    return infos;
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const moreList = await Promise.all<GetRowMoreInfo[]>(rowRefs.value.map((item: {
      getValue: () => Promise<GetRowMoreInfo>
    }) => item.getValue()));

    const infos = generateRequestParam(moreList);
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.PROXY_SCALE_DOWN,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    InfoBox({
      title: t('确认接入层缩容n个集群？', { n: totalNum.value }),
      subTitle: '请谨慎操作！',
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisProxyScaleDown',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            console.error('submit cluster shard update ticket error：', e);
            window.changeConfirm = false;
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-down-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
