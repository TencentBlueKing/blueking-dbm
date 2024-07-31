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
  <BkLoading :loading="isLoading">
    <div
      v-overflow-tips
      class="capacity-box"
      :class="{ 'default-display': !data }">
      <span
        v-if="!data"
        style="color: #c4c6cc">
        {{ t('选择集群后自动生成') }}
      </span>
      <div
        v-else
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            {{ data.currentVersion }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            {{ data.packageVersion }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            {{ data.moduleName }}
          </div>
        </div>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data?: {
      currentVersion: string;
      packageVersion: string;
      moduleName: string;
    };
    charset: string;
    isLoading: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .capacity-box {
    padding: 9px 16px;
    overflow: hidden;
    line-height: 26px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .display-content {
      display: flex;
      flex-direction: column;

      .content-item {
        display: flex;
        width: 100%;

        .item-title {
          width: 72px;
          text-align: right;
        }

        .item-content {
          flex: 1;
          display: flex;
          align-items: center;
          overflow: hidden;

          .percent {
            margin-left: 4px;
            font-size: 12px;
            font-weight: bold;
            color: #313238;
          }

          .spec {
            margin-left: 2px;
            font-size: 12px;
            color: #979ba5;
          }

          :deep(.render-spec-box) {
            height: 22px;
            padding: 0;
          }
        }
      }
    }
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }
</style>
