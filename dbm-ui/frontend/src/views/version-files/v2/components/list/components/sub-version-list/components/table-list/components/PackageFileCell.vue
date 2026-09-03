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
  <template
    v-for="(item, index) in data.packages"
    :key="index">
    <div
      v-if="index === 0 || isShowMore"
      class="package-file-cell">
      <div
        v-overflow-tips
        class="package-file-name">
        {{ item.name }}
      </div>
      <div class="package-file-tags">
        <BkTag
          v-if="item.permit_os?.length === 1"
          theme="info">
          {{ item.permit_os[0] }}
        </BkTag>
        <BkTag
          v-else-if="!item.permit_os?.length && item.permit_os_type === 'Windows'"
          theme="info">
          {{ `Windows ${t('全部')}` }}
        </BkTag>
        <BkTag
          v-else-if="item.permit_os?.length >= 2"
          v-bk-tooltips="{
            content: item.permit_os?.join('\n'),
          }"
          theme="info">
          {{ `${item.permit_os_type} x ${item.permit_os?.length}` }}
        </BkTag>
        <span v-else></span>
        <BkButton
          v-if="data.packages.length > 1 && index === 0"
          class="ml-6"
          text
          theme="primary"
          @click="handleToggleMoreList">
          {{ isShowMore ? t('收起') : t('+n个文件', { n: data.packages.length - 1 }) }}
        </BkButton>
      </div>
    </div>
  </template>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';

  interface Props {
    data: DbVersionModel;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isShowMore = ref(false);

  const handleToggleMoreList = () => {
    isShowMore.value = !isShowMore.value;
  };
</script>
<style lang="less">
  .package-file-cell {
    display: flex;

    & ~ .package-file-cell {
      margin-top: 4px;
    }

    .package-file-name {
      margin-right: 6px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }

    .package-file-tags {
      .bk-tag {
        cursor: pointer;
      }
    }
  }
</style>
