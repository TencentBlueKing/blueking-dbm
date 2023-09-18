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
  <div class="deployment-plan-operation-box">
    <DbForm form-type="vertical">
      <DbFormItem
        :label="t('方案名称')"
        required>
        <BkInput
          :maxlength="15"
          placeholder="推荐名称方式：总容量（分片大小 x  分片数），如：1500G (37.5G x 40分片）" />
      </DbFormItem>
      <DbFormItem
        :label="t('存储类型')"
        required>
        <BkInput />
      </DbFormItem>
      <DbFormItem
        :label="t('集群分片数量')"
        required>
        <BkInput type="number" />
      </DbFormItem>
      <div class="row">
        <div class="col">
          <DbFormItem
            :label="t('Proxy 资源规格')"
            required>
            <BkInput type="number" />
          </DbFormItem>
        </div>
        <div class="col">
          <DbFormItem
            :label="t('机器组数（每组 2 台）')"
            required>
            <BkInput type="number" />
          </DbFormItem>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <DbFormItem
            :label="t('后端存储资源规格')"
            required>
            <BkInput type="number" />
          </DbFormItem>
        </div>
        <div class="col">
          <DbFormItem
            :label="t('机器组数（每组 2 台）')"
            required>
            <BkInput type="number" />
          </DbFormItem>
        </div>
      </div>
    </DbForm>
    <div class="disk-box">
      集群预估容量：
      <span class="number-strong">300G</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
<style lang="less">
  .deployment-plan-operation-box {
    padding: 24px 40px;

    .row {
      display: flex;

      & ~ .row {
        margin-top: 24px;
      }
    }

    .col {
      flex: 1;

      & ~ .col {
        margin-left: 40px;
      }
    }

    .disk-box {
      display: flex;
      height: 50px;
      padding: 0 16px;
      margin-top: 24px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;
      align-items: center;

      .number-strong {
        font-weight: bold;
        color: #63656e;
      }
    }
  }
</style>
