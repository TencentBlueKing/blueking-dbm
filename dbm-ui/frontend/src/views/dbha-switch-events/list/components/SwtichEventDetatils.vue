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
  <div class="switch-event-details">
    <BkLog ref="logRef" />
  </div>
</template>

<script setup lang="ts">
  import { format } from 'date-fns';

  import { getEventSwitchLog } from '@services/source/dbha';

  import BkLog from '@components/vue2/bk-log/index.vue';

  type EventSwitchLogItem = ServiceReturnType<typeof getEventSwitchLog>[number]

  interface Props {
    uid: number
  }

  const props = defineProps<Props>();

  const logRef = ref();
  const isLoading = ref(false);

  const formatLogData = (data: EventSwitchLogItem[] = []) => {
    const regex = /^##\[[a-z]+]/;

    return data.map((item) => {
      const { timestamp, message, levelname } = item;
      const time = format(new Date(Number(timestamp)), 'yyyy-MM-dd HH:mm:ss');
      return {
        ...item,
        message: regex.test(message)
          ? message.replace(regex, (match: string) => `${match}[${time} ${levelname}]`)
          : `[${time} ${levelname}] ${message}`,
      };
    });
  };

  /**
   * 清空日志
   */
  const handleClearLog = () => {
    logRef.value.handleLogClear();
  };

  /**
   * 设置日志
   */
  const handleSetLog = (data: EventSwitchLogItem[] = []) => {
    logRef.value.handleLogAdd(data);
  };

  const fetchEventSwitchLog = () => {
    isLoading.value = true;
    getEventSwitchLog({ sw_id: props.uid })
      .then((res) => {
        handleClearLog();
        handleSetLog(formatLogData(res));
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  watch(() => props.uid, () => {
    props.uid && fetchEventSwitchLog();
  }, { immediate: true });
</script>

<style lang="less" scoped>
.switch-event-details {
  height: 100%;
  padding: 16px;
}
</style>
