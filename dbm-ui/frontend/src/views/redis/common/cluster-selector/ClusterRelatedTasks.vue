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
  <div class="panel">
    <div class="title">
      {{ $t('集群关联的其他任务') }}
    </div>
    <template v-if="data && data.length > 0">
      <div
        v-for="item in data"
        :key="item.flow_id"
        class="item">
        <DbIcon
          :class="{'loading-flag': item.status === PipelineStatus.RUNNING}"
          svg
          :type="item.status === PipelineStatus.RUNNING ?
            'sync-pending' : item.status === PipelineStatus.FAILED ? 'sync-failed' : 'sync-default'" />
        <span>【{{ item.title }}】{{ $t('单据ID：') }}</span>
        <span style="color:#3A84FF">#{{ item.ticket_id }}</span>
        <div
          v-if="item.status === PipelineStatus.FAILED"
          class="fail-tip">
          &nbsp;,&nbsp;<span style="color:#EA3636">{{ $t('执行失败') }}</span>&nbsp;,&nbsp;{{ $t('待确认') }}
        </div>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
  import RedisModel from '@services/model/redis/redis';

  import { PipelineStatus } from '@common/const';

  interface Props {
    data?: RedisModel['operations']
  }

  withDefaults(defineProps<Props>(), {
    data: undefined,

  });
</script>
<style lang="less" scoped>


.panel {
  display: flex;
  width: 100%;
  flex-direction: column;

  .title {
    height: 16px;
    margin-bottom: 8px;
    font-family: MicrosoftYaHei-Bold;
    font-size: 12px;
    font-weight: 700;
    color: #313238;
  }

  .item {
    display: flex;
    width: 100%;
    height: 20px;
    align-items: center;
    font-size: 12px;
    color: #63656E;

    .loading-flag {
      display: flex;
      color: #3a84ff;
      animation: rotate-loading 1s linear infinite;
    }
  }
}
</style>
