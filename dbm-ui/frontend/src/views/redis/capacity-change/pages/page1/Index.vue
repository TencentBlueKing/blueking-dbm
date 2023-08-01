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
    <div class="master-failover-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('集群容量变更：XXX')" />
      <RenderData
        class="mt16"
        @scroll-display="handleScrollDisplay"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :is-fixed="isFixed"
          :removeable="tableData.length < 2"
          :versions-map="versionsMap"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @click-select="() => handleClickSelect(index)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
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
      v-model:is-show="isShowMasterInstanceSelector"
      :tab-list="clusterSelectorTabList"
      @change="handelClusterChange" />
    <ChooseClusterTargetPlan
      :data="activeRowData"
      :is-show="showChooseClusterTargetPlan"
      :title="t('选择集群目标方案')"
      @click-cancel="() => showChooseClusterTargetPlan = false"
      @click-confirm="handleChoosedTargetCapacity" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getClusterTypeToVersions } from '@services/clusters';
  import RedisModel, { RedisClusterTypes } from '@services/model/redis/redis';
  import { listClusterList } from '@services/redis/toolbox';
  import type { FilterClusterSpecItem } from '@services/resourceSpec';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ChooseClusterTargetPlan, { type Props as TargetPlanProps } from '@views/redis/common/cluster-deploy-plan/Index.vue';
  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';


  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const showChooseClusterTargetPlan = ref(false);
  const activeRowData = ref<TargetPlanProps['data']>();
  const activeRowIndex = ref(0);
  const isFixed = ref(false);
  const versionsMap = ref<Record<string, string[]>>({});

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.targetCluster)).length);

  const clusterSelectorTabList = [ClusterTypes.REDIS];

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  onMounted(() => {
    queryDBVersions();
  });

  const queryDBVersions = async () => {
    const ret = await getClusterTypeToVersions();
    versionsMap.value = ret;
  };

  const handleScrollDisplay = (status: boolean) => {
    isFixed.value = status;
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (obj: FilterClusterSpecItem) => {
    const currentRow = tableData.value[activeRowIndex.value];
    currentRow.sepcId = obj.spec_id;
    currentRow.targetShardNum = obj.cluster_shard_num;
    currentRow.targetGroupNum = obj.machine_pair;
    currentRow.targetCapacity = {
      current: currentRow.currentCapacity?.total ?? 0,
      used: currentRow.currentCapacity?.used ?? 0,
      total: obj.cluster_capacity,
    };
    showChooseClusterTargetPlan.value = false;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.targetCluster;
  };

  // 点击目标容量
  const handleClickSelect = (index: number) => {
    activeRowIndex.value = index;
    const rowData = tableData.value[index];
    if (rowData.targetCluster) {
      const obj = {
        targetCluster: rowData.targetCluster,
        currentSepc: rowData.currentSepc ?? '',
        capacity: rowData.currentCapacity ?? { total: 1, used: 0 },
        clusterType: rowData.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance,
        shardNum: rowData.shardNum ?? 0,
      };
      activeRowData.value = obj;
      showChooseClusterTargetPlan.value = true;
    }
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (data: RedisModel) => {
    const specConfig = data.cluster_spec;
    const row = {
      rowKey: data.master_domain,
      isLoading: false,
      targetCluster: data.master_domain,
      currentSepc: `${specConfig.cpu.max}核${specConfig.mem.max}GB_${specConfig.storage_spec[0].size}GB_QPS:${specConfig.qps.max}`,
      clusterId: data.id,
      bkCloudId: data.bk_cloud_id,
      shardNum: data.cluster_shard_num,
      groupNum: data.machine_pair_cnt,
      version: data.major_version,
      clusterType: data.cluster_spec.spec_cluster_type,
      currentCapacity: {
        used: 1,
        total: data.cluster_capacity,
      },
    };
    return row;
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    const ret = await listClusterList(currentBizId, { domain });
    if (ret.length < 1) {
      return;
    }
    const data = ret[0];
    const row = generateRowDateFromRequest(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const { targetCluster } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[targetCluster];
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));

    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_SCALE_UPDOWN,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    InfoBox({
      title: t('确认提交 n 个集群容量变更任务？', { n: totalNum.value }),
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisCapacityChange',
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
            console.error('submit capacity change ticket error: ', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .master-failover-page {
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
