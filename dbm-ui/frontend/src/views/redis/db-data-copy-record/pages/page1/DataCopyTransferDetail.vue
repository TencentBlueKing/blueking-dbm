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
  <BkSideslider
    :before-close="handleBeforeClose"
    :is-show="isShow"
    :width="960"
    @closed="handleClose">
    <template #header>
      <div class="header-box">
        <span style="margin-right: 7px;">{{ $t('【数据复制】传输详情') }}</span>
        <BkTag>
          源集群：{{ data?.src_cluster }}
        </BkTag>
        <DbIcon
          style="margin-right: 6px;color: #979BA5;"
          svg
          type="arrow-right" />
        <BkTag>
          目标集群：{{ data?.src_cluster }}
        </BkTag>
      </div>
    </template>
    <div class="main-box">
      <BkCollapse
        v-model="activeIndex"
        class="bk-collapse-demo">
        <BkCollapsePanel
          name="base-info">
          <template #header>
            <div class="item-title">
              <DbIcon
                :class="{'active-icon': !activeIndex.includes('base-info')}"
                svg
                type="down-shape" />
              <span style="margin-left: 5px;">基础信息</span>
            </div>
          </template>
          <template #content>
            <div class="base-info">
              <div class="row-item">
                <div class="column-item">
                  <div class="title">
                    复制类型：
                  </div>
                  <div class="content">
                    {{ data?.dts_copy_type && copyTypesMap[data.dts_copy_type] }}
                  </div>
                </div>
                <div class="column-item">
                  <div class="title">
                    目标业务：
                  </div>
                  <div class="content">
                    {{ data?.dst_bk_biz_id && bizsMap[data.dst_bk_biz_id] }}
                  </div>
                </div>
              </div>
              <div class="row-item">
                <div class="column-item">
                  <div class="title">
                    状态：
                  </div>
                  <div class="content">
                    <ExecuteStatus :type="data?.status" />
                  </div>
                </div>
                <div class="column-item">
                  <div class="title">
                    关联单据：
                  </div>
                  <div class="content">
                    {{ data?.bill_id }}
                  </div>
                </div>
              </div>
              <div class="row-item">
                <div class="column-item">
                  <div class="title">
                    包含 Key：
                  </div>
                  <div class="content">
                    {{ data?.key_white_regex }}
                  </div>
                </div>
                <div class="column-item">
                  <div class="title">
                    忽略 key：
                  </div>
                  <div class="content">
                    {{ data?.key_black_regex }}
                  </div>
                </div>
              </div>
              <div class="row-item">
                <div class="column-item">
                  <div class="title">
                    写入类型：
                  </div>
                  <div class="content">
                    {{ data?.write_mode && writeModesMap[data.write_mode] }}
                  </div>
                </div>
                <div class="column-item">
                  <div class="title">
                    校验与修复类型：
                  </div>
                  <div class="content">
                    {{ data?.data_check_repair_type && repairAndVerifyModesMap[data.data_check_repair_type] }}
                  </div>
                </div>
              </div>
              <div class="row-item">
                <div class="column-item">
                  <div class="title">
                    断开设置：
                  </div>
                  <div class="content">
                    {{ data?.sync_disconnect_type && disconnectModesMap[data.sync_disconnect_type] }}
                  </div>
                </div>
                <div class="column-item">
                  <div class="title">
                    定时频率：
                  </div>
                  <div class="content">
                    {{ data?.sync_disconnect_reminder_frequency
                      && remindFrequencyModesMap[data.sync_disconnect_reminder_frequency] }}
                  </div>
                </div>
              </div>
              <div class="row-item">
                <div class="column-item">
                  <div class="title">
                    创建时间：
                  </div>
                  <div class="content">
                    {{ data?.create_time }}
                  </div>
                </div>
              </div>
            </div>
          </template>
        </BkCollapsePanel>
        <BkCollapsePanel
          name="detail">
          <template #header>
            <div class="item-title">
              <DbIcon
                :class="{'active-icon': !activeIndex.includes('detail')}"
                svg
                type="down-shape" />
              <span style="margin-left: 5px;">执行详情</span>
            </div>
          </template>
          <template #content>
            <div class="detail-box">
              <div class="operate-box">
                <BkButton
                  class="ml10"
                  theme="primary">
                  失败重试
                </BkButton>
                <BkInput
                  v-model="searchValue"
                  clearable
                  :placeholder="$t('请选择条件进行搜索')"
                  style="width:565px;"
                  type="search" />
              </div>
              <DbOriginalTable
                class="deploy-table"
                :columns="columns"
                :data="tableData" />
            </div>
          </template>
        </BkCollapsePanel>
      </BkCollapse>
    </div>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisDSTHistoryJobModel, { CopyModes, DisconnectModes, RemindFrequencyModes, RepairAndVerifyModes, WriteModes } from '@services/model/redis/redis-dst-history-job';
  import { getRedisDTSJobTasks } from '@services/redis/toolbox';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import ExecuteStatus, { TransmissionTypes } from './ExecuteStatus.vue';


  interface Props {
    data?: RedisDSTHistoryJobModel;
  }

  interface Emits {
    (e: 'on-close'): void
  }

  interface DataRow {
    src_instance: string;
    dts_server: string;
    task_type: string;
    status: TransmissionTypes;
    execute_time: string;
    reason: string;
    checked: boolean;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const globalBizsStore = useGlobalBizs();

  const { bizs } = globalBizsStore;

  const activeIndex =  ref(['base-info', 'detail']);
  const searchValue = ref('');
  const tableData = ref([
    {
      src_instance: '127.0.0.1',
      dts_server: '127.0.0.0',
      task_type: 'MakeCache',
      status: TransmissionTypes.END_OF_TRANSMISSION,
      execute_time: '2022-08-15  12:00:00',
      reason: '失败的原因失败的原因失败的原因失...',
      checked: false,
    },
    {
      src_instance: '127.0.0.1',
      dts_server: '127.0.0.0',
      task_type: 'MakeCache',
      status: TransmissionTypes.FULL_TRANSFERING,
      execute_time: '2022-08-15  12:00:00',
      reason: '失败的原因失败的原因失败的原因失...',
      checked: false,
    },
    {
      src_instance: '127.0.0.1',
      dts_server: '127.0.0.0',
      task_type: 'MakeCache',
      status: TransmissionTypes.INCREMENTAL_TRANSFER_FAILED,
      execute_time: '2022-08-15  12:00:00',
      reason: '失败的原因失败的原因失败的原因失...',
      checked: false,
    },
  ]);
  const timer = ref();

  const isSelectedAll = computed(() => tableData.value.filter(item => item.checked).length === tableData.value.length);

  const isIndeterminate = computed(() => tableData.value.filter(item => item.checked).length > 0);

  const columns = [
    {
      label: () => (
        <div style="display:flex;align-items:center;">
          <bk-checkbox
            label={t('源实例')}
            indeterminate={isSelectedAll.value ? false : isIndeterminate.value}
            model-value={isSelectedAll.value}
            onClick={(e: Event) => e.stopPropagation()}
            onChange={handleSelectPageAll}
        />
        </div>
      ),
      field: 'src_instance',
      render: ({ index, data }: {index: number, data: DataRow}) => <div style="display:flex;align-items:center;">
          <bk-checkbox
            label={data.src_instance}
            model-value={data.checked}
            onChange={() => handleSelectOne(index)}
        />
        </div>,
    },
    {
      label: 'DtsServer',
      field: 'dts_server',
    },
    {
      label: t('Task 类型'),
      field: 'task_type',
    },
    {
      label: t('执行状态'),
      field: 'status',
      render: ({ data }: { data: DataRow }) => <ExecuteStatus type={data.status} />,
    },
    {
      label: t('执行时间'),
      field: 'execute_time',
    },
    {
      label: t('失败原因'),
      field: 'reason',
    }];

  const bizsMap = bizs.reduce((result, item) => {
    result[String(item.bk_biz_id)] = item.name;
    return result;
  }, {} as Record<string, string>);

  const copyTypesMap = {
    [CopyModes.CROSS_BISNESS]: t('跨业务'),
    [CopyModes.INTRA_BISNESS]: t('业务内'),
    [CopyModes.INTRA_TO_THIRD]: t('业务内至第三方'),
    [CopyModes.SELFBUILT_TO_INTRA]: t('自建集群至业务内'),
  };

  const writeModesMap = {
    [WriteModes.DELETE_AND_WRITE_TO_REDIS]: t('先删除同名redis key，再执行写入'),
    [WriteModes.FLUSHALL_AND_WRITE_TO_REDIS]: t('先清空目标集群所有数据，再写入'),
    [WriteModes.KEEP_AND_APPEND_TO_REDIS]: t('保留同名redis key，追加写入'),
  };

  const repairAndVerifyModesMap = {
    [RepairAndVerifyModes.DATA_CHECK_AND_REPAIR]: t('数据校验并修复'),
    [RepairAndVerifyModes.DATA_CHECK_ONLY]: t('仅进行数据校验，不进行修复'),
    [RepairAndVerifyModes.NO_CHECK_NO_REPAIR]: t('不校验不修复'),
  };

  const disconnectModesMap = {
    [DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION]: t('复制完成后，自动断开'),
    [DisconnectModes.KEEP_SYNC_WITH_REMINDER]: t('不断开，定时发送断开提醒'),
  };

  const remindFrequencyModesMap = {
    [RemindFrequencyModes.ONCE_DAILY]: t('一天一次（早上 10:00）'),
    [RemindFrequencyModes.ONCE_WEEKLY]: t('一周一次（早上 10:00）'),
  };

  const tableRawData = tableData.value;
  watch(searchValue, (str) => {
    if (str) {
      clearTimeout(timer.value);
      timer.value = setTimeout(() => {
        tableData.value = tableRawData.filter(item => item.src_instance.includes(str) || item.dts_server.includes(str));
      }, 1000);
    } else {
      tableData.value = tableRawData;
    }
  });

  watch(() => props.data, (data) => {
    if (!data) {
      return;
    }
    queryTasksTableData(data);
  });

  const queryTasksTableData = async (data: RedisDSTHistoryJobModel) => {
    const r = await getRedisDTSJobTasks({
      bill_id: data.bill_id,
      src_cluster: data.src_cluster,
      dst_cluster: data.dst_cluster,
    });
    console.log('getRedisDTSJobTasks>>>', r);
  };

  const handleSelectPageAll = (checked: boolean) => {
    if (checked) {
      tableData.value.forEach(item => item.checked = true);
    } else {
      tableData.value.forEach(item => item.checked = false);
    }
  };

  const handleSelectOne = (index: number) => {
    tableData.value[index].checked = !tableData.value[index].checked;
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    emits('on-close');
  }

</script>

<style lang="less" scoped>

.active-icon {
  transform: rotateZ(-90deg);
  transition: all 0.2s;
}

.header-box {
  display: flex;
  width: 100%;
  align-items: center;
}

.item-title {
  display: flex;
  font-size: 14px;
  font-weight: 700;
  color: #313238;
  cursor: pointer;
}

.main-box {
  display: flex;
  width: 100%;
  padding: 24px;

  :deep(.bk-collapse-content) {
    padding: 0;
  }

}

.base-info {
  display: flex;
  width: 100%;
  flex-direction: column;
  padding: 16px 60px;

  .row-item {
    display: flex;
    width: 100%;

    .column-item {
      flex: 1;
      display: flex;
      align-items: center;

      .title {
        height: 32px;
        line-height: 32px;
        color: @default-color;
      }

      .content {
        margin-left: 5px;
        color: @title-color;
        flex: 1;
      }
    }
  }
}

.detail-box {
  display: flex;
  width: 100%;
  flex-direction: column;
  padding: 16px 0;

  .operate-box {
    display: flex;
    width: 100%;
    margin-bottom: 16px;
    justify-content: space-between;
  }
}

.deploy-table {
  .bk-table-head {
    :deep(tr) {
      th:first-child {
        width: 32px !important;
      }
    }
  }

  :deep(tr) {
    td:first-child {
      width: 32px !important;

      .selection {
        padding: 0 !important;
      }
    }


  }
}

.first-column {
  display: flex;
  align-items: center;
}

</style>
