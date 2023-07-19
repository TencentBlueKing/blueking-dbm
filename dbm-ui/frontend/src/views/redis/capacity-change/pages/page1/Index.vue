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
          @on-cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :tab-list="clusterSelectorTabList"
        @change="handelClusterChange" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ChooseClusterTargetPlan
      v-model:is-show="showChooseClusterTargetPlan"
      :data="activeRowData"
      @click-cancel="() => showChooseClusterTargetPlan = false"
      @click-confirm="handleChoosedTargetCapacity" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getClusterTypeToVersions } from '@services/clusters';
  import { RedisClusterTypes } from '@services/model/redis/redis';
  import RedisClusterSpecModel from '@services/model/resource-spec/redis-cluster-sepc';
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

  import RedisModel from '@/services/model/redis/redis';
  import RedisClusterNodeByFilterModel from '@/services/model/redis/redis-cluster-node-by-filter';

  interface GetRowMoreInfo {
    version: string,
    switchMode: OnlineSwitchType,
  }

  enum AffinityType {
    SAME_SUBZONE_CROSS_SWTICH = 'SAME_SUBZONE_CROSS_SWTICH', // 同城同subzone跨交换机跨机架
    SAME_SUBZONE = 'SAME_SUBZONE', // 同城同subzone
    CROS_SUBZONE = 'CROS_SUBZONE', // 同城跨subzone
    NONE = 'NONE', // 无需亲和性处理
  }

  interface InfoItem {
    cluster_id: number,
    bk_cloud_id: number,
    db_version: string,
    shard_num: number,
    group_num: number,
    online_switch_type: OnlineSwitchType,
    resource_spec: {
      backend_group: {
        spec_id: number,
        count: number, // 机器组数
        affinity: AffinityType, // 暂时固定 'CROS_SUBZONE',
      }
    }
  }


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
  const handleChoosedTargetCapacity = (obj: RedisClusterSpecModel) => {
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
  const generateRowDateFromRequest = (data: RedisClusterNodeByFilterModel) => {
    const specConfig = data.storage[0].machine__spec_config;
    const masters = data.storage.filter(item => item.instance_role === 'redis_master');
    const row: IDataRow = {
      rowKey: data.cluster.immute_domain,
      isLoading: false,
      targetCluster: data.cluster.immute_domain,
      currentSepc: `${specConfig.cpu.max}核${specConfig.mem.max}GB_${specConfig.storage_spec[0].size}GB_QPS:${specConfig.qps.max}`,
      clusterId: data.cluster.id,
      bkCloudId: data.cluster.bk_cloud_id,
      shardNum: masters.length,
      groupNum: new Set(...masters.map(item => item.machine__ip)).size,
      version: data.cluster.major_version,
      clusterType: data.cluster.cluster_type,
      currentCapacity: {
        used: 200,
        total: 250,
      },
    };
    return row;
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow [] = [];
    const domains = list.map(item => item.immute_domain);
    const clustersInfo = await getClusterInfo(domains);
    // 根据映射关系匹配
    clustersInfo.forEach((item) => {
      const domain = item.cluster.immute_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
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

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    const ret = await getClusterInfo(domain);
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

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (moreList: GetRowMoreInfo[]) => {
    const infos: InfoItem[] = [];
    tableData.value.forEach((item, index) => {
      if (item.targetCluster) {
        const obj: InfoItem = {
          cluster_id: item.clusterId,
          db_version: moreList[index].version,
          bk_cloud_id: item.bkCloudId,
          shard_num: item.targetShardNum ?? 0,
          group_num: item.targetGroupNum ?? 0,
          online_switch_type: moreList[index].switchMode,
          resource_spec: {
            backend_group: {
              spec_id: item.sepcId ?? 0,
              count: item.targetGroupNum ?? 0, // 机器组数
              affinity: AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
            },
          },
        };
        infos.push(obj);
      }
    });
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
