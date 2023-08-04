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
  <div class="status-box">
    <DbIcon
      svg
      :type="statusObj.type" />
    <span style="margin-left:7px;">
      {{ statusObj.text }}
    </span>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { TransmissionTypes } from '@services/model/redis/redis-dst-history-job';


  interface Props {
    type?: TransmissionTypes;
  }

  const props = withDefaults(defineProps<Props>(), {
    type: TransmissionTypes.END_OF_TRANSMISSION,
  });


  const { t } = useI18n();

  const statusObj = computed(() => {
    let text = '';
    let type = '';
    switch (props.type) {
    case TransmissionTypes.FULL_TRANSFERING: // 全量传输中
      text = t('全量传输中');
      type = 'sync-pending';
      break;
    case TransmissionTypes.INCREMENTAL_TRANSFERING: // 增量传输中
      text = t('增量传输中');
      type = 'sync-pending';
      break;
    case TransmissionTypes.FULL_TRANSFER_FAILED: // 全量传输失败
      text = t('全量传输失败');
      type = 'sync-failed';
      break;
    case TransmissionTypes.INCREMENTAL_TRANSFER_FAILED: // 增量传输失败
      text = t('增量传输失败');
      type = 'sync-failed';
      break;
    case TransmissionTypes.TO_BE_EXECUTED: // 待执行
      text = t('待执行');
      type = 'sync-default';
      break;
    case TransmissionTypes.END_OF_TRANSMISSION: // 传输结束
      text = t('传输结束');
      type = 'sync-success';
      break;
    case TransmissionTypes.TRANSSION_TERMINATE: // 传输终止
      text = t('传输终止');
      type = 'sync-waiting-01';
      break;
    default:
      text = t('传输结束');
      type = 'sync-success';
      break;
    }
    return {
      text,
      type,
    };
  });
</script>
<style lang="less" scoped>
.status-box {
  display: flex;
  align-items: center;
}
</style>
