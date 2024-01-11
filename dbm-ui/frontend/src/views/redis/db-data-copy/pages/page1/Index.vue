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
        :title="t('数据复制：通过DTS能力，将原集群全部或者部分数据复制到目标集群，原集群和目标集群都可以为自建集群或者DBM托管集群')" />
      <div
        class="title-spot"
        style="margin-top: 16px;">
        {{ t('复制类型') }}<span class="required" />
      </div>
      <div class="btn-group">
        <BkRadioGroup
          v-model="copyType"
          @change="handleChangeCopyType">
          <BkRadioButton
            v-for="item in copyTypeList"
            :key="item.value"
            :label="item.value">
            {{ item.label }}
          </BkRadioButton>
        </BkRadioGroup>
      </div>
      <Component
        :is="currentTable"
        ref="currentTableRef"
        :cluster-list="clusterList"
        @change-table-available="handleTableDataAvailableChange" />
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
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="w-88 ml-8"
          :disabled="isSubmitting"
          style="margin-left: 8px;">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="tsx">
// 业务内，通用
  export interface InfoItem {
    src_cluster: number | string,
    dst_cluster: number | string,
    key_white_regex:string, // 包含key
    key_black_regex:string, // 排除key
  }

  // 跨业务
  export type CrossBusinessInfoItem = InfoItem & { dst_bk_biz_id: number };

  // 业务内至第三方
  export type IntraBusinessToThirdInfoItem = InfoItem & { dst_cluster_password: string };

  // 自建集群至业务内
  export type SelfbuiltClusterToIntraInfoItem = InfoItem &
    { src_cluster_type: ClusterType, src_cluster_password: string };

  export const destroyLocalStorage = () => {
    setTimeout(() => {
      localStorage.removeItem(LocalStorageKeys.REDIS_DB_DATA_RECORD_RECOPY);
    });
  };
</script>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisDSTHistoryJobModel,
    {
      CopyModes,
      DisconnectModes,
      RemindFrequencyModes,
      RepairAndVerifyFrequencyModes,
      RepairAndVerifyModes,
      WriteModes,
    } from '@services/model/redis/redis-dst-history-job';
  import { getRedisList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import {
    LocalStorageKeys,
    TicketTypes,
  } from '@common/const';

  import {
    copyTypeList,
    disconnectTypeList,
    remindFrequencyTypeList,
    repairAndVerifyFrequencyList,
    repairAndVerifyTypeList,
    writeTypeList,
  } from '@views/redis/common/const';

  import RenderCrossBusinessTable from './components/cross-business/Index.vue';
  import RenderIntraBusinessToThirdPartTable from './components/intra-business-third/Index.vue';
  import type { SelectItem } from './components/RenderTargetCluster.vue';
  import RenderSelfbuiltToIntraBusinessTable  from './components/selfbuilt-clusters-intra-business/Index.vue';
  import { ClusterType } from './components/selfbuilt-clusters-intra-business/RenderClusterType.vue';
  import RenderWithinBusinessTable from './components/within-business/Index.vue';


  type InfoTypes = InfoItem | CrossBusinessInfoItem | IntraBusinessToThirdInfoItem | SelfbuiltClusterToIntraInfoItem;

  // 提交单据类型
  type DataCopySubmitTicket = SubmitTicket<TicketTypes, InfoTypes[]> & {
    details: {
      dts_copy_type: CopyModes,
      write_mode: WriteModes,
      sync_disconnect_setting: {
        type: DisconnectModes,
        reminder_frequency: RemindFrequencyModes | '',
      },
      data_check_repair_setting: {
        type: RepairAndVerifyModes | '',
        execution_frequency: RepairAndVerifyFrequencyModes | '',
      }
    }
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
  const clusterList = ref<SelectItem[]>([]);
  const currentTableRef = ref();

  const currentTable = computed(() => {
    const comMap = {
      [CopyModes.INTRA_BISNESS]: RenderWithinBusinessTable,
      [CopyModes.CROSS_BISNESS]: RenderCrossBusinessTable,
      [CopyModes.INTRA_TO_THIRD]: RenderIntraBusinessToThirdPartTable,
      [CopyModes.SELFBUILT_TO_INTRA]: RenderSelfbuiltToIntraBusinessTable,
    };
    return copyType.value in comMap ? comMap[copyType.value as keyof typeof comMap]
      : RenderSelfbuiltToIntraBusinessTable;
  });

  onMounted(() => {
    checkandRecoverDataListFromLocalStorage();
    queryClusterList();
  });


  const checkandRecoverDataListFromLocalStorage = () => {
    const r = localStorage.getItem(LocalStorageKeys.REDIS_DB_DATA_RECORD_RECOPY);
    if (!r) {
      return;
    }
    const item = JSON.parse(r) as RedisDSTHistoryJobModel;
    copyType.value = item.dts_copy_type;
    writeType.value = item.write_mode;
    disconnectType.value = item.sync_disconnect_type;
    remindFrequencyType.value = item.sync_disconnect_reminder_frequency;
    repairAndVerifyType.value = item.data_check_repair_type;
    repairAndVerifyFrequency.value = item.data_check_repair_execution_frequency;
  };

  const handleTableDataAvailableChange = (status: boolean) => {
    submitDisable.value = !status;
  };

  const handleChangeCopyType = () => {
    submitDisable.value = true;
    destroyLocalStorage();
  };

  const queryClusterList = async () => {
    const result = await getRedisList({
      offset: 0,
      limit: -1,
    });
    clusterList.value = result.results.map(item => ({
      value: item.id,
      label: item.master_domain,
    }));
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (infos: InfoTypes[]) => {
    const isAutoDisconnect = disconnectType.value === DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION;
    const params: DataCopySubmitTicket = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_DATA_COPY,
      details: {
        dts_copy_type: copyType.value,
        write_mode: writeType.value,
        // 断开设置与提醒频率
        sync_disconnect_setting: {
          type: disconnectType.value,
          reminder_frequency: isAutoDisconnect ? '' : remindFrequencyType.value,
        },
        data_check_repair_setting: {
          type: isAutoDisconnect ? '' : repairAndVerifyType.value,
          execution_frequency: isAutoDisconnect || repairAndVerifyType.value === RepairAndVerifyModes.NO_CHECK_NO_REPAIR ? '' : repairAndVerifyFrequency.value,
        },
        infos,
      },
    };
    return params;
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await currentTableRef.value.getValue();
    const params = generateRequestParam(infos);
    InfoBox({
      title: t('确认复制n个集群数据？', { n: params.details.infos.length }),
      subTitle: t('将会把源集群的数据复制到对应的新集群'),
      width: 480,
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
  const handleReset = async () => {
    await currentTableRef.value.resetTable();
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
