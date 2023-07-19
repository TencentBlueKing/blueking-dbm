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
    <div class="proxy-scale-up-page">
      <BkAlert
        closable
        theme="info"
        title="扩容接入层：XXX" />
      <RenderData
        class="mt16"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
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
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes  } from '@common/const';

  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';
  import { getClusterInfo } from '@views/redis/common/utils';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type MoreDataItem,
  } from './components/Row.vue';

  import RedisModel from '@/services/model/redis/redis';
  import RedisClusterNodeByFilterModel from '@/services/model/redis/redis-cluster-node-by-filter';

  interface InfoItem {
    cluster_id: number,
    bk_cloud_id: number,
    target_proxy_count: number,
    resource_spec: {
      proxy: {
        spec_id: number,
        count: number
      }
    }
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const totalNum = computed(() => tableData.value.filter(item => item.cluster !== '').length);

  const clusterSelectorTabList = [ClusterTypes.REDIS];
  // 集群域名是否已存在表格的映射表
  let domainMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.cluster;
  };

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow [] = [];
    const domains = list.map(item => item.immute_domain);
    const clustersInfo = await getClusterInfo(domains);
    const clustersMap: Record<string, RedisClusterNodeByFilterModel> = {};
    // 建立映射关系
    clustersInfo.forEach((item) => {
      clustersMap[item.cluster.immute_domain] = item;
    });
    // 根据映射关系匹配
    clustersInfo.forEach((item) => {
      const domain = item.cluster.immute_domain;
      if (!domainMemo[domain]) {
        const row = {
          rowKey: item.cluster.immute_domain,
          isLoading: false,
          cluster: item.cluster.immute_domain,
          clusterId: item.cluster.id,
          bkCloudId: item.cluster.bk_cloud_id,
          clusterType: item.cluster.cluster_type,
          nodeType: 'Proxy',
          spec: {
            ...item.proxy[0].machine__spec_config,
          },
          targetNum: '1',
        };
        row.spec.count = item.proxy.length;
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
    if (ret.length > 0) {
      const data = ret[0];
      const row = {
        rowKey: data.cluster.immute_domain,
        isLoading: false,
        cluster: data.cluster.immute_domain,
        clusterId: data.cluster.id,
        bkCloudId: data.cluster.bk_cloud_id,
        clusterType: data.cluster.cluster_type,
        nodeType: 'Proxy',
        spec: {
          ...data.proxy[0].machine__spec_config,
        },
        targetNum: '1',
      };
      row.spec.count = data.proxy.length,
      tableData.value[index] = row;
      domainMemo[domain] = true;
    }
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const { cluster } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[cluster];
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (moreList: MoreDataItem[]) => {
    const infos: InfoItem[] = [];
    tableData.value.forEach((item, index) => {
      if (item.cluster) {
        const proxyCount = moreList[index].targetNum;
        const obj: InfoItem = {
          cluster_id: item.clusterId,
          bk_cloud_id: item.bkCloudId,
          target_proxy_count: proxyCount,
          resource_spec: {
            proxy: {
              spec_id: moreList[index].specId,
              count: item.spec?.count ? proxyCount - item.spec.count : 0,
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
    const moreList = await Promise.all<MoreDataItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<MoreDataItem>
    }) => item.getValue()));

    const infos = generateRequestParam(moreList);
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.PROXY_SCALE_UP,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    InfoBox({
      title: t('确认扩容接入层n个集群？', { n: totalNum.value }),
      subTitle: t('请谨慎操作！'),
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisProxyScaleUp',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            console.error('proxy scale up submit ticket error：', e);
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
  .proxy-scale-up-page {
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

  .bottom-btn {
    width: 88px;
  }
</style>
