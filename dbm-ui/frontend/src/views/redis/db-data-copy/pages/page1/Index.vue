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
        :title="$t('数据迁移（DTS）：主机级别操作，即同机所有集群均会完成主从关系互切')" />
      <div
        class="title-spot"
        style="margin-top: 16px;">
        复制类型<span class="edit-required" />
      </div>
      <div class="btn-group">
        <BkRadioGroup
          v-model="copyType">
          <BkRadioButton
            v-for="item in copyTypeList"
            :key="item"
            :label="item" />
        </BkRadioGroup>
      </div>
      <RenderWithinBusinessTable
        v-if="copyType === CopyModes.INTRA_BISNESS"
        ref="withinBusinessTableRef"
        :cluster-list="clusterList"
        @on-change-table-available="handleTableDataAvailableChange" />
      <RenderCrossBusinessTable
        v-if="copyType === CopyModes.CROSS_BISNESS"
        ref="crossBusinessTableRef"
        :cluster-list="clusterList" />
      <RenderIntraBusinessToThirdPartTable
        v-if="copyType === CopyModes.INTRA_TO_THIRD"
        ref="intraBusinessToThirdPartTableRef"
        :cluster-list="clusterList" />
      <RenderSelfbuiltToIntraBusinessTable
        v-if="copyType === CopyModes.SELFBUILT_TO_INTRA"
        ref="selfbuiltToIntraBusinessTableRef"
        :cluster-list="clusterList" />
      <div
        class="title-spot"
        style="margin-top: 25px;">
        写入类型<span class="edit-required" />
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
      <div class="title-spot">
        断开设置<span class="edit-required" />
      </div>
      <BkRadioGroup
        v-model="disconnectType">
        <BkRadio
          v-for="item in disconnectTypeList"
          :key="item.value"
          :label="item.value">
          {{ item.label }}
        </BkRadio>
      </BkRadioGroup>
      <template v-if="disconnectType !== DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION">
        <div class="title-spot">
          提醒频率<span class="edit-required" />
        </div>
        <BkRadioGroup
          v-model="remindFrequencyType">
          <BkRadio
            v-for="item in remindFrequencyTypeList"
            :key="item.value"
            :label="item.value">
            {{ item.label }}
          </BkRadio>
        </BkRadioGroup>
        <div class="title-spot">
          校验与修复类型<span class="edit-required" />
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
        <template v-if="repairAndVerifyType !== RepairAndVerifyModes.NO_CHECK_NO_REPAIR">
          <div
            class="title-spot"
            style="margin-top: 25px;">
            校验与修复频率设置<span class="edit-required" />
          </div>
          <BkSelect
            v-model="repairAndVerifyFrequency"
            class="select-box">
            <BkOption
              v-for="(item, index) in repairAndVerifyFrequencyList"
              :key="index"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
        </template>
      </template>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="submitDisable"
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
          class="w-88 ml8"
          :disabled="isSubmitting"
          style="margin-left: 8px;">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { listClusterList } from '@services/redis/toolbox';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@views/redis/common/cluster-selector/ClusterSelector.vue';
  import { getClusterInfo } from '@views/redis/common/utils';

  import RenderCrossBusinessTable from './cross-business/Index.vue';
  import RenderIntraBusinessToThirdPartTable from './Intra-business-third/Index.vue';
  import RenderSelfbuiltToIntraBusinessTable  from './selfbuilt-clusters-intra-business/Index.vue';
  import { ClusterType } from './selfbuilt-clusters-intra-business/RenderClusterType.vue';
  import RenderWithinBusinessTable from './within-business/Index.vue';
  import type { TableRealRowData as IntraBusinessTableRealData } from './within-business/Row.vue';

  import RedisModel from '@/services/model/redis/redis';
  import RedisClusterNodeByFilterModel from '@/services/model/redis/redis-cluster-node-by-filter';

  interface GetRowMoreInfo {
    targetNum: string;
  }

  // 业务内，通用
  interface InfoItem {
    src_cluster: string,
    dst_cluster: string,
    key_white_regex:string, // 包含key
    key_black_regex:string, // 排除key
  }

  // 跨业务
  type CrossBusinessInfoItem = InfoItem & { dst_bk_biz_id: number };

  // 业务内至第三方
  type IntraBusinessToThirdInfoItem = InfoItem & { dst_cluster_password: string };

  // 自建集群至业务内
  type SelfbuiltClusterToIntraInfoItem = InfoItem & { src_cluster_type: ClusterType, src_cluster_password: string };

  // 提交单据类型
  type DataCopySubmitTicket<T> = SubmitTicket<TicketTypes, T[]> & {
    details: {
      dts_copy_type: 'one_app_diff_cluster',
      write_mode: WriteModes,
      sync_disconnect_setting: {
        type: DisconnectModes,
        reminder_frequency?: RemindFrequencyModes,
      },
      data_check_repair_setting?: {
        type: RepairAndVerifyModes,
        execution_frequency: RepairAndVerifyFrequencyModes,
      }
    }
  }

  const enum CopyModes {
    INTRA_BISNESS = '业务内',
    CROSS_BISNESS = '跨业务',
    INTRA_TO_THIRD = '业务内至第三方',
    SELFBUILT_TO_INTRA = '自建集群至业务内',
  }

  enum WriteModes {
    DELETE_AND_WRITE_TO_REDIS = 'delete_and_write_to_redis', // 先删除同名redis key, 在执行写入 (如: del $key + hset $key)
    KEEP_AND_APPEND_TO_REDIS = 'keep_and_append_to_redis', // 保留同名redis key,追加写入
    FLUSHALL_AND_WRITE_TO_REDIS = 'flushall_and_write_to_redis', // 先清空目标集群所有数据,在写入
  }

  enum DisconnectModes {
    AUTO_DISCONNECT_AFTER_REPLICATION = 'auto_disconnect_after_replication', // 复制完成后，自动断开
    KEEP_SYNC_WITH_REMINDER = 'keep_sync_with_reminder', // 不断开，定时发送断开提醒
  }

  enum RemindFrequencyModes {
    ONCE_DAILY = 'once_daily', // 一天一次
    ONCE_WEEKLY = 'once_weekly', // 一周一次
  }

  enum RepairAndVerifyModes {
    DATA_CHECK_AND_REPAIR = 'data_check_and_repair', // 数据校验并修复
    DATA_CHECK_ONLY = 'data_check_only', // 仅进行数据校验，不进行修复
    NO_CHECK_NO_REPAIR = 'no_check_no_repair', // 不校验不修复
  }

  enum RepairAndVerifyFrequencyModes {
    ONCE_AFTER_REPLICATION= 'once_after_replication', // 复制完成后，只进行一次
    ONCE_EVERY_THREE_DAYS = 'once_every_three_days', // 复制完成后，每三天一次
    ONCE_WEEKLY = 'once_weekly', // 复制完成后，每周一次
  }


  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const rowRefs = ref();
  const isSubmitting  = ref(false);

  const tableData = ref([]);
  const copyType = ref(CopyModes.INTRA_BISNESS);
  const writeType = ref(WriteModes.DELETE_AND_WRITE_TO_REDIS);
  const disconnectType = ref(DisconnectModes.KEEP_SYNC_WITH_REMINDER);
  const remindFrequencyType = ref(RemindFrequencyModes.ONCE_DAILY);
  const repairAndVerifyType = ref(RepairAndVerifyModes.DATA_CHECK_AND_REPAIR);
  const repairAndVerifyFrequency = ref(RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION);
  const submitDisable = ref(true);
  const clusterList = ref<string[]>([]);
  const withinBusinessTableRef = ref();
  const crossBusinessTableRef = ref();
  const intraBusinessToThirdPartTableRef = ref();
  const selfbuiltToIntraBusinessTableRef = ref();


  const copyTypeList = [
    CopyModes.INTRA_BISNESS,
    CopyModes.CROSS_BISNESS,
    CopyModes.INTRA_TO_THIRD,
    CopyModes.SELFBUILT_TO_INTRA,
  ];

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

  const disconnectTypeList = [
    {
      label: '复制完成后，自动断开',
      value: DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION,
    },
    {
      label: '不断开，定时发送断开提醒',
      value: DisconnectModes.KEEP_SYNC_WITH_REMINDER,
    },
  ];

  const remindFrequencyTypeList = [
    {
      label: '一天一次（早上 10:00）',
      value: RemindFrequencyModes.ONCE_DAILY,
    },
    {
      label: '一周一次（早上 10:00）',
      value: RemindFrequencyModes.ONCE_WEEKLY,
    },
  ];

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

  const repairAndVerifyFrequencyList = [
    {
      value: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
      label: '复制完成后，只进行一次',
    },
    {
      value: RepairAndVerifyFrequencyModes.ONCE_EVERY_THREE_DAYS,
      label: '复制完成后，每三天一次',
    },
    {
      value: RepairAndVerifyFrequencyModes.ONCE_WEEKLY,
      label: '复制完成后，每周一次',
    },
  ];

  onMounted(() => {
    queryClusterList();
  });

  const handleTableDataAvailableChange = (status: boolean) => {
    submitDisable.value = !status;
  };

  const queryClusterList = async () => {
    const arr = await listClusterList();
    clusterList.value = arr.map(item => item.immute_domain);
  };


  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (dataList: IntraBusinessTableRealData[]) => {
    const infos = dataList.map((item) => {
      const obj: InfoItem = {
        src_cluster: item.srcCluster,
        dst_cluster: item.targetCluster,
        key_white_regex: item.includeKey.join('\n'), // 包含key
        key_black_regex: item.excludeKey.join('\n'), // 排除key
      };
      return obj;
    });
    const params: DataCopySubmitTicket<InfoItem> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_DATA_COPY,
      details: {
        dts_copy_type: 'one_app_diff_cluster',
        write_mode: writeType.value,
        sync_disconnect_setting: {
          type: disconnectType.value,
          reminder_frequency: remindFrequencyType.value,
        },
        data_check_repair_setting: {
          type: repairAndVerifyType.value,
          execution_frequency: repairAndVerifyFrequency.value,
        },
        infos,
      },
    };
    return params;
  };

  // 提交 业务内
  const submitIntraBusiness = async () => {
    const dataList = await withinBusinessTableRef.value.getValue() as IntraBusinessTableRealData[];
    console.log('dataList: ', dataList);
    const params = generateRequestParam(dataList);
    console.log('submit params: ', params);
  };

  // 提交 跨业务
  const submitCrossBusiness = async () => {
    const dataList = await crossBusinessTableRef.value.getValue();
    console.log('dataList: ', dataList);
  };

  // 提交 业务内至第三方
  const submitIntraBusinessToThird = async () => {
    const dataList = await intraBusinessToThirdPartTableRef.value.getValue();
    console.log('dataList: ', dataList);
  };

  // 提交 自建集群至业务内
  const submitSelfbuiltToIntraBusiness = async () => {
    const dataList = await selfbuiltToIntraBusinessTableRef.value.getValue();
    console.log('dataList: ', dataList);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    switch (copyType.value) {
    case CopyModes.INTRA_BISNESS:
      // 业务内
      await submitIntraBusiness();
      break;
    case CopyModes.CROSS_BISNESS:
      // 跨业务
      await submitCrossBusiness();
      break;
    case CopyModes.INTRA_TO_THIRD:
      // 业务内至第三方
      await submitIntraBusinessToThird();
      break;
    default:
      // 自建集群至业务内
      await submitSelfbuiltToIntraBusiness();
      break;
    }

    // const infos = generateRequestParam(moreList);
    // const params: SubmitTicket<TicketTypes, InfoItem[]> = {
    //   bk_biz_id: currentBizId,
    //   ticket_type: TicketTypes.PROXY_SCALE_DOWN,
    //   details: {
    //     ip_source: 'resource_pool',
    //     infos,
    //   },
    // };
    // InfoBox({
    //   title: t('确认接入层缩容n个集群？', { n: totalNum.value }),
    //   subTitle: '请谨慎操作！',
    //   width: 480,
    //   infoType: 'warning',
    //   onConfirm: () => {
    //     isSubmitting.value = true;
    //     createTicket(params).then((data) => {
    //       console.log('createTicket result: ', data);
    //       window.changeConfirm = false;
    //       router.push({
    //         name: 'RedisProxyScaleDown',
    //         params: {
    //           page: 'success',
    //         },
    //         query: {
    //           ticketId: data.id,
    //         },
    //       });
    //     })
    //       .catch((e) => {
    //         // 目前后台还未调通
    //         console.error('单据提交失败：', e);
    //         // 暂时先按成功处理
    //         window.changeConfirm = false;
    //         router.push({
    //           name: 'RedisProxyScaleDown',
    //           params: {
    //             page: 'success',
    //           },
    //           query: {
    //             ticketId: '',
    //           },
    //         });
    //       })
    //       .finally(() => {
    //         isSubmitting.value = false;
    //       });
    //   } });
  };

  // 重置
  const handleReset = () => {
    // tableData.value = [createRowData()];
    // domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>

  .proxy-scale-down-page {
    padding-bottom: 20px;

    .title-spot {
      position: relative;
      width: 100%;
      height: 20px;
      margin-top: 22px;
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 700;
      color: #63656E;

      .edit-required {
        position: relative;

        &::after {
          position: absolute;
          top: -10px;
          margin-left: 4px;
          font-size: 12px;
          line-height: 40px;
          color: #ea3636;
          content: "*";
        }
      }
    }

    .btn-group {
      margin-bottom: 16px;

      :deep(.bk-radio-button) {
        width: 180px;
      }
    }

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

    .select-box {
      width: 460px;
    }
  }
</style>

