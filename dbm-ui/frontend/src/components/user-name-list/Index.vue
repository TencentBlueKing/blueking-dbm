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
  <div class="dbm-user-name-list">
    <bk-user-display-name
      class="dbm-user-name-list-name"
      :user-id="data.join(',')" />
    <div
      v-if="data.length > 0"
      v-bk-tooltips="t('复制所有')"
      class="dbm-user-name-list-copy"
      @click.stop="handleCopy">
      <DbIcon type="copy" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  interface Props {
    data: string[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // 复制原始用户名而不是展示用的中文名，方便直接粘贴到其他系统
  const handleCopy = () => {
    execCopy(props.data.join('\n'), t('复制成功，共n条', { n: props.data.length }));
  };
</script>

<style lang="less">
  .dbm-user-name-list {
    display: inline-flex;
    max-width: 100%;
    align-items: center;

    &:hover {
      .dbm-user-name-list-copy {
        opacity: 100%;
      }
    }

    .dbm-user-name-list-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .dbm-user-name-list-copy {
      padding-left: 8px;
      color: #3a84ff;
      cursor: pointer;
      opacity: 0%;
      flex-shrink: 0;
    }
  }
</style>
