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
  <div class="batch-assign-list-panel">
    <div class="title">
      <span>
        {{ t('已选主机') }}
      </span>
      <BkPopover
        :arrow="false"
        :is-show="isShowHostActionPop"
        placement="bottom"
        theme="light export-host-action-extends"
        trigger="manual">
        <div
          class="host-action"
          :class="{
            active: isShowHostActionPop,
          }"
          @blur="handleHideHostAction"
          @click="handleShowHostAction">
          <DbIcon type="more" />
        </div>
        <template #content>
          <div
            class="item"
            @click="handleCopyAll">
            {{ t('复制所有 IP') }}
          </div>
        </template>
      </BkPopover>
    </div>
    <div class="host-header">
      <DbIcon
        class="mr-6"
        type="down-big" />
      <I18nT keypath="共n台">
        <span
          class="number"
          style="color: #3a84ff">
          {{ hostList.length }}
        </span>
      </I18nT>
    </div>
    <div class="host-list">
      <div
        v-for="hostItem in hostList"
        :key="hostItem.bk_host_id"
        class="host-item">
        <div>{{ hostItem.ip }}</div>
        <div class="action-box">
          <DbIcon
            v-bk-tooltips="t('复制')"
            type="copy"
            @click="handleCopy(hostItem)" />
          <DbIcon
            v-bk-tooltips="t('删除')"
            style="font-size: 16px"
            type="close"
            @click="handleRemove(hostItem)" />
        </div>
      </div>
      <BkException
        v-if="hostList.length < 1"
        :description="t('暂无数据')"
        scene="part"
        type="empty" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { useCopy } from '@hooks';

  import { messageWarn } from '@utils';

  interface Expose {
    getValue: () => Promise<any>;
  }

  const hostList = defineModel<DbResourceModel[]>({
    default: () => [],
  });

  const copy = useCopy();
  const { t } = useI18n();

  const formRef = ref();
  const isShowHostActionPop = ref(false);
  const formData = reactive({
    for_biz: '',
    resource_type: '',
    labels: '',
  });

  const handleShowHostAction = () => {
    isShowHostActionPop.value = true;
  };

  const handleHideHostAction = () => {
    isShowHostActionPop.value = false;
  };

  // 复制所有主机 IP
  const handleCopyAll = () => {
    const ipList = hostList.value.map((item) => item.ip);
    isShowHostActionPop.value = false;
    if (!ipList.length) {
      messageWarn(t('暂无可复制 IP'));
      return;
    }

    copy(ipList.join('\n'));
  };

  // 复制单个指定主机 IP
  const handleCopy = (hostItem: DbResourceModel) => {
    copy(hostItem.ip);
  };

  // 删除单个主机
  const handleRemove = (hostItem: DbResourceModel) => {
    const hostListResult = hostList.value.reduce<DbResourceModel[]>((result, item) => {
      if (item.bk_host_id !== hostItem.bk_host_id) {
        result.push(item);
      }
      return result;
    }, []);

    hostList.value = hostListResult;
  };

  defineExpose<Expose>({
    getValue() {
      return formRef.value.validate().then(() => ({
        for_biz: Number(formData.for_biz),
        resource_type: formData.resource_type,
        labels: formData.labels,
      }));
    },
  });
</script>
<style lang="less">
  .batch-assign-list-panel {
    display: flex;
    height: 100%;
    background: #f5f6fa;
    flex-direction: column;

    .title {
      padding: 8px 12px 10px 24px;
      font-weight: 700;
      font-size: 12px;
      color: #313238;
      background: #ffffff;
      border: 1px solid #dcdee5;
      border-radius: 0 2px 2px 0;
      display: flex;

      .host-action {
        display: flex;
        width: 20px;
        height: 20px;
        margin-left: auto;
        cursor: pointer;
        border-radius: 2px;
        transition: all 0.15s;
        align-items: center;
        justify-content: center;

        &.active,
        &:hover {
          background: #e1ecff;
        }
      }
    }

    .host-header {
      display: flex;
      align-items: center;
      padding: 0 24px;
      margin-top: 14px;
      margin-bottom: 4px;
      line-height: 24px;
      color: #63656e;
      font-size: 12px;
    }

    .host-list {
      padding: 0 24px;
      overflow-y: auto;
      font-size: 12px !important;

      .host-item {
        display: flex;
        height: 32px;
        padding: 0 12px;
        line-height: 1;
        color: #63656e;
        background-color: #fff;
        border-radius: 2px;
        transition: all 0.15s;
        align-items: center;

        & ~ .host-item {
          margin-top: 2px;
        }

        &:hover {
          background-color: #e1ecff;

          .action-box {
            display: flex;
          }
        }

        .action-box {
          display: none;
          margin-left: auto;
          color: #3a84ff;
          align-items: center;

          i {
            padding: 0 2px;
            cursor: pointer;
          }
        }
      }
    }
  }

  [data-theme~='export-host-action-extends'] {
    padding: 8px 0 !important;

    .item {
      display: flex;
      height: 32px;
      padding: 0 12px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      transition: all 0.15s;
      align-items: center;

      &:hover {
        color: #3a84ff;
        background-color: #e1ecff;
      }
    }
  }
</style>
