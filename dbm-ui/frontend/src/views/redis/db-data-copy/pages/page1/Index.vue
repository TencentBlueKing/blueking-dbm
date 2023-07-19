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
        {{ t('复制类型') }}<span class="required" />
      </div>
      <div class="btn-group">
        <BkRadioGroup
          v-model="copyType">
          <BkRadioButton
            v-for="item in copyTypeList"
            :key="item.value"
            :label="item.value">
            {{ item.label }}
          </BkRadioButton>
        </BkRadioGroup>
      </div>
      <RenderWithinBusinessTable
        v-if="copyType === CopyModes.INTRA_BISNESS"
        ref="withinBusinessTableRef"
        :cluster-list="clusterList"
        @on-change-table-available="handleTableDataAvailableChange" />
      <RenderCrossBusinessTable
        v-else-if="copyType === CopyModes.CROSS_BISNESS"
        ref="crossBusinessTableRef"
        :cluster-list="clusterList"
        @on-change-table-available="handleTableDataAvailableChange" />
      <RenderIntraBusinessToThirdPartTable
        v-else-if="copyType === CopyModes.INTRA_TO_THIRD"
        ref="intraBusinessToThirdPartTableRef"
        :cluster-list="clusterList"
        @on-change-table-available="handleTableDataAvailableChange" />
      <RenderSelfbuiltToIntraBusinessTable
        v-else-if="copyType === CopyModes.SELFBUILT_TO_INTRA"
        ref="selfbuiltToIntraBusinessTableRef"
        :cluster-list="clusterList"
        @on-change-table-available="handleTableDataAvailableChange" />
      <div
        class="title-spot"
        style="margin: 25px 0 12px;">
        {{ t('写入类型') }}<span class="required" />
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
      <div
        class="title-spot"
        style="margin: 22px 0 12px;">
        {{ t('断开设置') }}<span class="required" />
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
        <div
          class="title-spot"
          style="margin: 22px 0 12px;">
          {{ t('提醒频率') }}<span class="required" />
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
        <div
          class="title-spot"
          style="margin: 22px 0 12px;">
          {{ t('校验与修复类型') }}<span class="required" />
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
            style="margin: 25px 0 7px;">
            {{ t('校验与修复频率设置') }}<span class="required" />
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
<script lang="ts">
  export const enum CopyModes {
    INTRA_BISNESS = 'one_app_diff_cluster', // 业务内
    CROSS_BISNESS = 'diff_app_diff_cluster', // 跨业务
    INTRA_TO_THIRD = 'copy_to_other_system', // 业务内至第三方
    SELFBUILT_TO_INTRA = 'user_built_to_dbm', // 自建集群至业务内
  }
</script>
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { listClusterList } from '@services/redis/toolbox';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import RenderCrossBusinessTable from './cross-business/Index.vue';
  import type { TableRealRowData as CrossBusinessTableRealData } from './cross-business/Row.vue';
  import RenderIntraBusinessToThirdPartTable from './intra-business-third/Index.vue';
  import type { TableRealRowData as IntraBusinessToThirdTableRealData } from './intra-business-third/Row.vue';
  import RenderSelfbuiltToIntraBusinessTable  from './selfbuilt-clusters-intra-business/Index.vue';
  import { ClusterType } from './selfbuilt-clusters-intra-business/RenderClusterType.vue';
  import type { TableRealRowData as SelfbuiltToIntraBusinessTableRealData } from './selfbuilt-clusters-intra-business/Row.vue';
  import RenderWithinBusinessTable from './within-business/Index.vue';
  import type { TableRealRowData as IntraBusinessTableRealData } from './within-business/Row.vue';

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

  type DataList = IntraBusinessTableRealData[] | CrossBusinessTableRealData[] |
    IntraBusinessToThirdTableRealData[] | SelfbuiltToIntraBusinessTableRealData[];

  type InfoTypes = InfoItem | CrossBusinessInfoItem | IntraBusinessToThirdInfoItem | SelfbuiltClusterToIntraInfoItem;

  // 提交单据类型
  type DataCopySubmitTicket = SubmitTicket<TicketTypes, InfoTypes[]> & {
    details: {
      dts_copy_type: CopyModes,
      write_mode: WriteModes,
      sync_disconnect_setting: {
        type: DisconnectModes,
        reminder_frequency?: RemindFrequencyModes,
      },
      data_check_repair_setting?: {
        type: RepairAndVerifyModes,
        execution_frequency?: RepairAndVerifyFrequencyModes,
      }
    }
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
  const isSubmitting  = ref(false);
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
    {
      label: '业务内',
      value: CopyModes.INTRA_BISNESS,
    },
    {
      label: '跨业务',
      value: CopyModes.CROSS_BISNESS,
    },
    {
      label: '业务内至第三方',
      value: CopyModes.INTRA_TO_THIRD,
    },
    {
      label: '自建集群至业务内',
      value: CopyModes.SELFBUILT_TO_INTRA,
    },
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

  // 切换模式后，提交按钮失效
  watch(() => copyType.value, () => {
    submitDisable.value = true;
  });

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
  const generateRequestParam = (dataList: DataList, mode: CopyModes) => {
    let infos;
    switch (mode) {
    case CopyModes.INTRA_BISNESS:
      // 业务内
      infos = dataList.map((item) => {
        const obj = {
          src_cluster: item.srcCluster,
          dst_cluster: item.targetCluster,
          key_white_regex: item.includeKey.join('\n'), // 包含key
          key_black_regex: item.excludeKey.join('\n'), // 排除key
        };
        return obj;
      });

      break;
    case CopyModes.CROSS_BISNESS:
      // 跨业务
      infos = (dataList as CrossBusinessTableRealData[]).map((item) => {
        const obj = {
          src_cluster: item.srcCluster,
          dst_cluster: item.targetCluster,
          dst_bk_biz_id: item.targetBusines,
          key_white_regex: item.includeKey.join('\n'),
          key_black_regex: item.excludeKey.join('\n'),
        };
        return obj;
      });
      break;
    case CopyModes.INTRA_TO_THIRD:
      // 业务内至第三方
      infos = (dataList as IntraBusinessToThirdTableRealData[]).map((item) => {
        const obj = {
          src_cluster: item.srcCluster,
          dst_cluster: item.targetCluster,
          dst_cluster_password: item.password,
          key_white_regex: item.includeKey.join('\n'),
          key_black_regex: item.excludeKey.join('\n'),
        };
        return obj;
      });
      break;
    default:
      // 自建集群至业务内
      infos = (dataList as SelfbuiltToIntraBusinessTableRealData[]).map((item) => {
        const obj = {
          src_cluster: item.srcCluster,
          dst_cluster: item.targetCluster,
          src_cluster_type: item.clusterType,
          src_cluster_password: item.password,
          key_white_regex: item.includeKey.join('\n'),
          key_black_regex: item.excludeKey.join('\n'),
        };
        return obj;
      });
      break;
    }
    const params: DataCopySubmitTicket = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_DATA_COPY,
      details: {
        dts_copy_type: copyType.value,
        write_mode: writeType.value,
        // 断开设置与提醒频率
        sync_disconnect_setting: {
          type: disconnectType.value,
          reminder_frequency: remindFrequencyType.value,
        },
        infos,
      },
    };
    if (disconnectType.value === DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION) {
      delete params.details.sync_disconnect_setting.reminder_frequency;
      delete params.details.data_check_repair_setting;
    } else {
      // 校验与修复类型与校验与修复频率设置
      if (repairAndVerifyType.value !== RepairAndVerifyModes.NO_CHECK_NO_REPAIR) {
        params.details.data_check_repair_setting = {
          type: repairAndVerifyType.value,
          execution_frequency: repairAndVerifyFrequency.value,
        };
      } else {
        params.details.data_check_repair_setting = {
          type: repairAndVerifyType.value,
        };
      }
    }
    return params;
  };

  // 提交 业务内
  const submitIntraBusiness = async () => {
    const dataList = await withinBusinessTableRef.value.getValue();
    return generateRequestParam(dataList, CopyModes.INTRA_BISNESS);
  };

  // 提交 跨业务
  const submitCrossBusiness = async () => {
    const dataList = await crossBusinessTableRef.value.getValue();
    return generateRequestParam(dataList, CopyModes.CROSS_BISNESS);
  };

  // 提交 业务内至第三方
  const submitIntraBusinessToThird = async () => {
    const dataList = await intraBusinessToThirdPartTableRef.value.getValue();
    return generateRequestParam(dataList, CopyModes.INTRA_TO_THIRD);
  };

  // 提交 自建集群至业务内
  const submitSelfbuiltToIntraBusiness = async () => {
    const dataList = await selfbuiltToIntraBusinessTableRef.value.getValue();
    return generateRequestParam(dataList, CopyModes.SELFBUILT_TO_INTRA);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    let params: DataCopySubmitTicket;
    switch (copyType.value) {
    case CopyModes.INTRA_BISNESS:
      // 业务内
      params = await submitIntraBusiness();
      break;
    case CopyModes.CROSS_BISNESS:
      // 跨业务
      params = await submitCrossBusiness();
      break;
    case CopyModes.INTRA_TO_THIRD:
      // 业务内至第三方
      params = await submitIntraBusinessToThird();
      break;
    default:
      // 自建集群至业务内
      params = await submitSelfbuiltToIntraBusiness();
      break;
    }
    console.log('submit params: ', params);
    InfoBox({
      title: t('确认复制n个集群数据？', { n: params.details.infos.length }),
      subTitle: t('将会把源集群的数据复制到对应的新集群'),
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisDBDataCopy',
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
            console.error('submit data copy ticket error', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>

  .proxy-scale-down-page {
    padding-bottom: 20px;

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

