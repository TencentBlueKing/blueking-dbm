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
    <div class="recover-from-ins-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('回写数据：xxx')" />
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
          @on-cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div
        class="title-spot"
        style="margin: 25px 0 12px;">
        写入类型<span class="required" />
      </div>
      <BkRadioGroup
        v-model="writeType">
        <BkRadio
          v-for="item in writeTypeList"
          :key="item.value"
          :label="item.value">
          {{ item.label }}
        </BkRadio>
      </BkRadioGroup>
    </div>

    <template #action>
      <BkButton
        class="w-88"
        :disabled="totalNum === 0"
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
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :tab-list="clusterSelectorTabList"
      @change="handelClusterChange" />
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


  interface InfoItem {
    src_cluster: string;
    dst_cluster: string;
    key_white_regex: string;
    key_black_regex: string;
  }

  enum WriteModes {
    DELETE_AND_WRITE_TO_REDIS = 'delete_and_write_to_redis', // 先删除同名redis key, 在执行写入 (如: del $key + hset $key)
    KEEP_AND_APPEND_TO_REDIS = 'keep_and_append_to_redis', // 保留同名redis key,追加写入
    FLUSHALL_AND_WRITE_TO_REDIS = 'flushall_and_write_to_redis', // 先清空目标集群所有数据,在写入
  }

  type SubmitTicketType = SubmitTicket<TicketTypes, InfoItem[]>
    & { details: { dts_copy_type: string; write_mode: WriteModes } };

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isSubmitting  = ref(false);
  const writeType = ref(WriteModes.DELETE_AND_WRITE_TO_REDIS);

  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.srcCluster)).length);

  const clusterSelectorTabList = [ClusterTypes.REDIS];

  const writeTypeList = [
    {
      label: '先删除同名 Key，再写入（如：del  $key+ hset $key）',
      value: WriteModes.DELETE_AND_WRITE_TO_REDIS,
    },
    {
      label: '保留同名 Key，追加写入（如：hset $key）',
      value: WriteModes.KEEP_AND_APPEND_TO_REDIS,
    },
    {
      label: '清空目标集群所有数据，再写入',
      value: WriteModes.FLUSHALL_AND_WRITE_TO_REDIS,
    },
  ];

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};


  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };


  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster];
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow[] = [];
    const domains = list.map(item => item.immute_domain);
    const clustersInfo = await getClusterInfo(domains);
    clustersInfo.forEach((item) => {
      const domain = item.cluster.immute_domain;
      if (!domainMemo[domain]) {
        const row: IDataRow = {
          rowKey: item.cluster.immute_domain,
          isLoading: false,
          srcCluster: item.cluster.immute_domain,
          targetTime: '',
          targetCluster: '',
          includeKey: ['*'],
          excludeKey: [],
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
    const row: IDataRow = {
      rowKey: data.cluster.immute_domain,
      isLoading: false,
      srcCluster: data.cluster.immute_domain,
      targetTime: '',
      targetCluster: '',
      includeKey: ['*'],
      excludeKey: [],
    };
    tableData.value[index] = row;
    domainMemo[domain] = true;
  };


  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = async () => {
    const moreList = await Promise.all<MoreDataItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<MoreDataItem>
    }) => item.getValue()));

    const infos: InfoItem[] = [];
    tableData.value.forEach((item, index) => {
      if (item.srcCluster) {
        const obj = {
          src_cluster: item.srcCluster,
          dst_cluster: item.targetCluster,
          key_white_regex: moreList[index].includeKey.join('\n'),
          key_black_regex: moreList[index].excludeKey.join('\n'),
        };
        infos.push(obj);
      }
    });
    return infos;
  };

  // 提交
  const handleSubmit = async () => {
    const infos = await generateRequestParam();
    const params: SubmitTicketType = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_DATA_COPY,
      details: {
        dts_copy_type: 'copy_from_rollback_instance',
        write_mode: writeType.value,
        infos,
      },
    };
    InfoBox({
      title: t('确认对n个构造实例进行恢复？', { n: totalNum.value }),
      subTitle: t('请谨慎操作！'),
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisRecoverFromInstance',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            console.error('recover from instance ticket error', e);
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
  .recover-from-ins-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
