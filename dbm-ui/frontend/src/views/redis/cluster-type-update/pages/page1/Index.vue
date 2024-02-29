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
    <div class="cluster-shard-update">
      <BkAlert
        closable
        theme="info"
        :title="t('集群类型变更：通过部署新集群来实现原集群的类型变更，可以指定新的版本')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :cluster-types-map="clusterTypesMap"
          :data="item"
          :inputed-clusters="inputedClusters"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div
        class="title-spot"
        style="margin: 22px 0 12px">
        {{ t('校验与修复类型') }}<span class="required" />
      </div>
      <BkRadioGroup v-model="repairAndVerifyType">
        <BkRadio :label="RepairAndVerifyModes.DATA_CHECK_AND_REPAIR">
          <BkPopover
            placement="top"
            theme="dark">
            <span>{{ t(repairAndVerifyTypeList[0].label) }}</span>
            <template #content>
              <div>{{ t('校验：将会对集群进行大量的读操作，可能会影响性能。') }}</div>
              <div>{{ t('修复：修复将会覆盖同名 Key 对应的数据（覆盖更新，非追加）') }}</div>
            </template>
          </BkPopover>
        </BkRadio>
        <BkRadio :label="RepairAndVerifyModes.DATA_CHECK_ONLY">
          <BkPopover
            :content="t('校验将会对集群进行大量的读操作，可能会影响性能')"
            placement="top"
            theme="dark">
            <span>{{ t(repairAndVerifyTypeList[1].label) }}</span>
          </BkPopover>
        </BkRadio>
        <BkRadio :label="RepairAndVerifyModes.NO_CHECK_NO_REPAIR">
          {{ t(repairAndVerifyTypeList[2].label) }}
        </BkRadio>
      </BkRadioGroup>
      <template v-if="repairAndVerifyType !== RepairAndVerifyModes.NO_CHECK_NO_REPAIR">
        <div
          class="title-spot"
          style="margin: 25px 0 7px">
          {{ t('校验与修复频率设置') }}<span class="required" />
        </div>
        <BkSelect
          v-model="repairAndVerifyFrequency"
          style="width: 460px">
          <BkOption
            v-for="(item, index) in repairAndVerifyFrequencyList"
            :key="index"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
      </template>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import { RepairAndVerifyFrequencyModes, RepairAndVerifyModes } from '@services/model/redis/redis-dst-history-job';
  import { getRedisList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';
  import { getClusterTypeToVersions } from '@services/source/version';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/redis/common/const';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  type SubmitType = SubmitTicket<TicketTypes, InfoItem[]> & {
    details: {
      data_check_repair_setting: {
        type: RepairAndVerifyModes;
        execution_frequency: RepairAndVerifyFrequencyModes | '';
      };
    };
  };

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const rowRefs = ref();
  const isShowClusterSelector = ref(false);
  const isSubmitting = ref(false);
  const repairAndVerifyType = ref(RepairAndVerifyModes.DATA_CHECK_AND_REPAIR);
  const repairAndVerifyFrequency = ref(RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION);
  const tableData = ref([createRowData()]);
  const clusterTypesMap = ref<Record<string, string[]>>({});
  const selectedClusters = shallowRef<{ [key: string]: Array<RedisModel> }>({ [ClusterTypes.REDIS]: [] });
  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.srcCluster)).length);
  const inputedClusters = computed(() => tableData.value.map((item) => item.srcCluster));

  // 集群域名是否已存在表格的映射表
  let domainMemo = {} as Record<string, boolean>;

  onMounted(() => {
    queryDBVersions();
  });

  // 查询全部的集群类型映射表
  const queryDBVersions = async () => {
    const ret = await getClusterTypeToVersions();
    clusterTypesMap.value = ret;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  const generateTableRow = (item: RedisModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    srcCluster: item.master_domain,
    clusterId: item.id,
    bkCloudId: item.bk_cloud_id,
    switchMode: t('需人工确认'),
    currentSepc: `${item.cluster_capacity}G_${item.cluster_spec.qps.max}/s${t('（n 分片）', { n: item.cluster_shard_num })}`,
    currentCapacity: {
      used: 1,
      total: item.cluster_capacity,
    },
    currentSpecId: item.cluster_spec.spec_id,
    srcClusterType: item.cluster_type_name,
    clusterType: item.cluster_type,
    currentShardNum: item.cluster_shard_num,
    dbVersion: item.major_version,
    specConfig: {
      cpu: item.cluster_spec.cpu,
      id: item.cluster_spec.spec_id,
      mem: item.cluster_spec.mem,
      qps: item.cluster_spec.qps,
    },
    proxy: {
      id: item.proxy[0].spec_config.id,
      count: new Set(item.proxy.map((item) => item.ip)).size,
    },
  });

  // 批量选择
  const handelClusterChange = async (selected: { [key: string]: Array<RedisModel> }) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.REDIS];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateTableRow(item);
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

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    if (!domain) {
      const cluster = tableData.value[index].srcCluster;
      domainMemo[cluster] = false;
      tableData.value[index].srcCluster = '';
      return;
    }
    tableData.value[index].isLoading = true;
    // TODO: 使用精确查询接口替换
    const result = await getRedisList({ domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length < 1) {
      return;
    }
    const list = result.results.filter((item) => item.master_domain === domain);
    if (list.length === 0) {
      return;
    }
    const item = list[0];
    const row = generateTableRow(item);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.REDIS].push(item);
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
    const clustersArr = selectedClusters.value[ClusterTypes.REDIS];
    selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter((item) => item.master_domain !== srcCluster);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(
      rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue()),
    );
    const params: SubmitType = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_TYPE_UPDATE,
      details: {
        ip_source: 'resource_pool',
        data_check_repair_setting: {
          type: repairAndVerifyType.value,
          execution_frequency:
            repairAndVerifyType.value === RepairAndVerifyModes.NO_CHECK_NO_REPAIR ? '' : repairAndVerifyFrequency.value,
        },
        infos,
      },
    };
    InfoBox({
      title: t('确认对n个集群执行类型变更？', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params)
          .then((data) => {
            window.changeConfirm = false;
            router.push({
              name: 'RedisClusterTypeUpdate',
              params: {
                page: 'success',
              },
              query: {
                ticketId: data.id,
              },
            });
          })
          .catch((e) => {
            console.error('submit cluster shard update ticket error: ', e);
            window.changeConfirm = false;
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      },
    });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.REDIS] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .cluster-shard-update {
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
