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
  <BkDialog
    class="mongo-access-entry"
    :is-show="isShow"
    :quick-close="false"
    :title="t('获取访问方式')"
    width="1000"
    @closed="handleClose">
    <div class="copy-info">
      <BkButton
        text
        theme="primary"
        @click="handleCopyAll">
        {{ t('复制信息') }}
      </BkButton>
    </div>
    <div class="mongo-access-entry-content">
      <div
        v-for="(item, index) in dataList"
        :key="index"
        class="mongo-access-entry-item">
        <span class="mongo-access-entry-item-label">{{ item.label }}：</span>
        <span class="mongo-access-entry-item-value">{{ item.value || '--' }}</span>
        <BkButton
          v-bk-tooltips="t('复制xxx', [item.label])"
          class="copy-btn"
          text
          theme="primary">
          <DbIcon
            type="copy"
            @click="execCopy(item.value)" />
        </BkButton>
      </div>
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import MongodbDetailModel from '@services/model/mongodb/mongodb-detail';

  import { execCopy } from '@utils';

  interface Props {
    data: MongodbModel | MongodbDetailModel;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const dataList = computed(() => {
    const { data } = props;
    const infoList = [
      {
        label: t('集群名称'),
        value: data.cluster_name,
      },
      {
        label: t('域名'),
        value: data.entryDomain,
      },
      {
        label: t('连接字符串'),
        value: data.entryAccess,
      },
    ];

    if (data.entryAccessClb) {
      infoList.push({
        label: t('连接字符串（CLB）'),
        value: data.entryAccessClb,
      });
    }

    return infoList;
  });

  const handleCopyAll = () => {
    const content = dataList.value.map((dataItem) => `${dataItem.label}：${dataItem.value}`);
    execCopy(content.join('\n'));
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .mongo-access-entry {
    .copy-info {
      position: absolute;
      top: -18px;
      left: 160px;
    }

    .mongo-access-entry-content {
      padding-bottom: 8px;
      font-size: @font-size-mini;
    }

    .mongo-access-entry-item {
      display: flex;
      padding-bottom: 16px;

      .mongo-access-entry-item-label {
        flex-shrink: 0;
        width: 118px;
        text-align: right;
      }

      .mongo-access-entry-item-value {
        color: @title-color;
        word-break: break-all;
      }

      &:hover {
        .copy-btn {
          visibility: visible;
        }
      }

      .copy-btn {
        margin-left: 4px;
        visibility: hidden;
      }
    }
  }
</style>
