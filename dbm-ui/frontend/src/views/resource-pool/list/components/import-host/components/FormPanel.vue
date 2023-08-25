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
  <div class="import-host-form-panel">
    <div class="title">
      {{ t('导入设置') }}
    </div>
    <div class="host-header">
      <div>
        <I18nT keypath="已选n台">
          <span
            class="number"
            style="color: #3A84FF">
            {{ hostList.length }}
          </span>
        </I18nT>
      </div>
      <BkPopover
        :arrow="false"
        :is-show="isShowHostActionPop"
        placement="bottom"
        theme="light export-host-action-extends"
        trigger="manual">
        <div
          class="host-action"
          :class="{
            active: isShowHostActionPop
          }"
          @click="handleShowHostAction">
          <DbIcon type="more" />
        </div>
        <template #content>
          <div
            class="item"
            @click="handleRemoveAll">
            {{ t('清除所有') }}
          </div>
          <div
            class="item"
            @click="handleRemoveAbnormal">
            {{ t('清除异常 IP') }}
          </div>
          <div
            class="item"
            @click="handleCopyAll">
            {{ t('复制所有 IP') }}
          </div>
          <div
            class="item"
            @click="handleCopyAbnormal">
            {{ t('复制异常 IP') }}
          </div>
        </template>
      </BkPopover>
    </div>
    <div class="host-list">
      <div
        v-for="hostItem in hostList"
        :key="hostItem.host_id"
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
        :description="t('暂无数据，请从左侧添加对象')"
        scene="part"
        type="empty" />
    </div>
    <div class="more-info-form">
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          label="专用业务"
          property="for_bizs">
          <div class="com-input">
            <BkSelect
              v-model="formData.for_bizs"
              :disabled="isSetEmptyBiz"
              :loading="isBizListLoading"
              multiple>
              <BkOption
                v-for="bizItem in bizList"
                :key="bizItem.bk_biz_id"
                :label="bizItem.display_name"
                :value="bizItem.bk_biz_id" />
            </BkSelect>
            <BkCheckbox
              v-model="isSetEmptyBiz"
              class="ml-12">
              {{ t('无限制') }}
            </BkCheckbox>
          </div>
        </BkFormItem>
        <BkFormItem
          label="专用 DB"
          property="resource_types">
          <div class="com-input">
            <BkSelect
              v-model="formData.resource_types"
              :disabled="isSetEmptyResourceType"
              :loading="isDbTypeListLoading"
              multiple>
              <BkOption
                v-for="item in dbTypeList"
                :key="item.id"
                :label="item.name"
                :value="item.id" />
            </BkSelect>
            <BkCheckbox
              v-model="isSetEmptyResourceType"
              class="ml-12">
              {{ t('无限制') }}
            </BkCheckbox>
          </div>
        </BkFormItem>
      </DbForm>
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    reactive,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/common';
  import { fetchDbTypeList } from '@services/infras';
  import type ImportHostModel from '@services/model/db-resource/import-host';

  import { useCopy } from '@hooks';

  import { messageWarn } from '@utils';

  interface Props {
    hostList: ImportHostModel[]
  }
  interface Emits{
    (e: 'update:hostList', value: Props['hostList']): void,
  }
  interface Expose {
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const copy = useCopy();
  const { t } = useI18n();

  const formRef = ref();
  const isShowHostActionPop = ref(false);
  const isSetEmptyBiz = ref(false);
  const isSetEmptyResourceType = ref(false);
  const formData = reactive({
    for_bizs: [],
    resource_types: [],
  });

  const {
    data: bizList,
    loading: isBizListLoading,
  } = useRequest(getBizs);

  const {
    data: dbTypeList,
    loading: isDbTypeListLoading,
  } = useRequest(fetchDbTypeList);

  const handleShowHostAction = () => {
    isShowHostActionPop.value = true;
  };
  // 清空所有主机
  const handleRemoveAll = () => {
    emits('update:hostList', []);
    isShowHostActionPop.value = false;
  };
  // 清空所有异常主机
  const handleRemoveAbnormal = () => {
    const result = props.hostList.reduce((result, item) => {
      if (item.alive !== 0) {
        result.push(item);
      }
      return result;
    }, [] as Props['hostList']);
    emits('update:hostList', result);
    isShowHostActionPop.value = false;
  };
  // 复制所有主机 IP
  const handleCopyAll = () => {
    const ipList = props.hostList.map(item => item.ip);
    isShowHostActionPop.value = false;
    if (ipList.length < 1) {
      messageWarn(t('暂无可复制 IP'));
      return;
    }

    copy(ipList.join('\n'));
  };
  // 复制所有异常主机 IP
  const handleCopyAbnormal = () => {
    const ipList = props.hostList.reduce((result, item) => {
      if (item.alive === 0) {
        result.push(item.ip);
      }
      return result;
    }, [] as string[]);

    isShowHostActionPop.value = false;

    if (ipList.length < 1) {
      messageWarn(t('暂无可复制 IP'));
      return;
    }

    copy(ipList.join('\n'));
  };
  // 复制单个指定主机 IP
  const handleCopy = (hostItem: ImportHostModel) => {
    copy(hostItem.ip);
  };
  // 删除单个主机
  const handleRemove = (hostItem: ImportHostModel) => {
    const hostListResult = props.hostList.reduce((result, item) => {
      if (item.host_id !== hostItem.host_id) {
        result.push(item);
      }
      return result;
    }, [] as ImportHostModel[]);

    emits('update:hostList', hostListResult);
  };

  defineExpose<Expose>({
    getValue() {
      return formRef.value.validate()
        .then(() => ({
          for_bizs: isSetEmptyBiz.value ? [] : formData.for_bizs,
          resource_types: isSetEmptyResourceType.value ? [] : formData.resource_types,
        }));
    },
  });

</script>
<style lang="less">
.import-host-form-panel {
  display: flex;
  height: 100%;
  background: #f5f6fa;
  flex-direction: column;

  .title {
    padding: 12px 24px 0;
    font-size: 14px;
    line-height: 22px;
    color: #313238;
  }

  .host-header {
    display: flex;
    padding: 0 24px;
    margin-top: 14px;
    margin-bottom: 4px;
    line-height: 24px;
    color: #63656e;

    .host-action {
      display: flex;
      width: 20px;
      height: 20px;
      margin-left: auto;
      cursor: pointer;
      border-radius: 2px;
      transition: all .15s;
      align-items: center;
      justify-content: center;

      &.active,
      &:hover {
        background: #E1ECFF;
      }
    }
  }

  .host-list {
    height: calc(100% - 290px);
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

        .action-box{
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

  .more-info-form {
    padding: 15px 24px 30px;
    margin-top: auto;
    background: #fff;
    box-shadow: 0 -2px 4px 0 #0000001a;
  }

  .com-input {
    display: flex;

    .bk-select {
      flex: 1
    }
  }
}

[data-theme~="export-host-action-extends"] {
  padding: 8px 0 !important;

  .item {
    display: flex;
    height: 32px;
    padding: 0 12px;
    font-size: 12px;
    color: #63656E;
    cursor: pointer;
    transition: all .15s;
    align-items: center;

    &:hover {
      color: #3A84FF;
      background-color: #E1ECFF;
    }
  }
}
</style>
