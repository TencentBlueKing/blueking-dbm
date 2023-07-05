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
        title="集群容量变更：XXX" />
      <RenderData
        class="mt16"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          :version-list="versionList"
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
    <ChooseClusterTargetPlan
      v-model:is-show="showChooseClusterTargetPlan"
      :cluster-name="choosedClusterName"
      @on-confirm="handleChoosedTargetCapacity" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';
  import { getClusterInfo, getRedisVersions } from '@views/redis/common/utils';

  import ChooseClusterTargetPlan from './components/ChooseClusterTargetPlan.vue';
  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  import RedisModel from '@/services/model/redis/redis';
  import RedisClusterNodeByFilterModel from '@/services/model/redis/redis-cluster-node-by-filter';

  interface GetRowMoreInfo {
    scaleUpPlan: string;
    version: string;
  }

  interface InfoItem {
    cluster_id: number,
    db_version: string,
    resource_spec: {
      redis_scale_down_hosts: {
        resource_plan_id: number,
        count: number
      }
    }
  }


  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = ref<Array<IDataRow>>([createRowData()]);
  const versionList = ref<{
    id: string;
    name: string
  }[]>([]);
  const showChooseClusterTargetPlan = ref(false);
  const choosedClusterName = ref('');
  const totalNum = computed(() => tableData.value.filter(item => item.cluster !== '').length);

  const clusterSelectorTabList = [ClusterTypes.REDIS];

  // 集群域名是否已存在表格的映射表
  const domainMemo = {} as Record<string, boolean>;

  onMounted(() => {
    fetchVersions();
  });

  const handleChoosedTargetCapacity = (value: string) => {
    console.log(value);
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return firstRow.cluster;
  };

  const handleClickSelect = (index: number) => {
    console.log('index: ', index);
    choosedClusterName.value = tableData.value[index].cluster;
    showChooseClusterTargetPlan.value = true;
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList = [] as IDataRow [];
    const domains = list.map(item => item.immute_domain);
    const clustersInfo = await getClusterInfo(domains);
    if (clustersInfo) {
      const clustersMap: Record<string, RedisClusterNodeByFilterModel> = {};
      // 建立映射关系
      clustersInfo.forEach((item) => {
        clustersMap[item.cluster.immute_domain] = item;
      });
      // 根据映射关系匹配
      clustersInfo.forEach((item) => {
        const domain = item.cluster.immute_domain;
        if (!domainMemo[domain]) {
          const row: IDataRow = {
            rowKey: item.cluster.immute_domain,
            isLoading: false,
            cluster: item.cluster.immute_domain,
            clusterId: item.cluster.id,
            version: item.cluster.major_version,
            currentPlan: '暂无方案',
          };
          newList.push(row);
          domainMemo[domain] = true;
        }
      });
    }
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
    console.log('getClusterInfo: ', ret);
    if (ret) {
      const data = ret[0];
      const row: IDataRow = {
        rowKey: data.cluster.immute_domain,
        isLoading: false,
        cluster: data.cluster.immute_domain,
        clusterId: data.cluster.id,
        version: data.cluster.major_version,
        currentPlan: '暂无方案', // TODO: 方案未定
      };
      tableData.value[index] = row;
      domainMemo[domain] = true;
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
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (moreList: GetRowMoreInfo[]) => {
    const dataArr = tableData.value.filter(item => item.cluster !== '');
    const infos = dataArr.map((item, index) => {
      const obj: InfoItem = {
        cluster_id: item.clusterId,
        db_version: moreList[index].version,
        resource_spec: {
          redis_scale_down_hosts: {
            resource_plan_id: 0, // TODO: 方案未定
            count: 0,
          },
        },
      };
      return obj;
    });
    return infos;
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    console.log('submit: ', tableData.value);
    const moreList = await Promise.all<GetRowMoreInfo[]>(rowRefs.value.map((item: {
      getValue: () => Promise<GetRowMoreInfo>
    }) => item.getValue()));

    const infos = generateRequestParam(moreList);
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_SCALE_UP,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    console.log('request param: ', params);
    InfoBox({
      title: t('确认扩容存储层n个集群？', { n: totalNum.value }),
      subTitle: '请谨慎操作！',
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          console.log('createTicket result: ', data);
          window.changeConfirm = false;
          router.push({
            name: 'RedisStorageScaleUp',
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
              name: 'RedisStorageScaleUp',
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

  const handleReset = () => {
    tableData.value = [createRowData()];
  };

  // 获取 redis 版本信息
  const fetchVersions = async () => {
    const list = await getRedisVersions();
    if (list) versionList.value = list;
  };
</script>

<style lang="less">
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
