<!--
  TencentBlueKing is pleased to support the open source community by making
  蓝鲸智云 - 审计中心 (BlueKing - Audit Center) available.
  Copyright (C) 2023 THL A29 Limited,
  a Tencent company. All rights reserved.
  Licensed under the MIT License (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at http://opensource.org/licenses/MIT
  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on
  an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the License for the
  specific language governing permissions and limitations under the License.
  We undertake not to change the open source license (MIT license) applicable
  to the current version of the project delivered to anyone in the future.
-->
<template>
  <div>
    <div class="no-permission-tips">
      <img
        class="lock"
        src="/static/images/no-permission.svg">
      <p class="tips-text">
        {{ t('该操作需要以下权限') }}
      </p>
    </div>
    <div class="permission-list">
      <table>
        <thead>
          <tr>
            <th>{{ t('系统') }}</th>
            <th>{{ t('需要申请的权限') }}</th>
            <th>{{ t('关联的资源实例') }}</th>
          </tr>
        </thead>
        <tbody v-if="data.apply_url">
          <template
            v-for="(permissionItem, index) in data.permissionList"
            :key="index">
            <tr>
              <td>{{ permissionItem.systemName }}</td>
              <td>{{ permissionItem.actionName }}</td>
              <td>
                <p
                  v-for="(resourceItem, rindex) in permissionItem.relatedResources"
                  :key="rindex">
                  {{ resourceItem.type }}-{{ resourceItem.instances.join('，') }}
                </p>
                <p v-if="permissionItem.relatedResources.length < 1">
                  --
                </p>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div
        v-if="!data.apply_url"
        class="permission-list-empty">
        {{ t('你已拥有权限，请刷新页面') }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type ApplyDataModel from '@services/model/iam/apply-data';

  interface Props {
    data: ApplyDataModel
  }
  defineProps<Props>();
  const { t } = useI18n();

</script>
<style lang="less" scoped>
  .no-permission-tips {
    padding-top: 30px;
    text-align: center;

    .lock {
      width: 120px;
      height: 100px;
    }

    .tips-text {
      margin: 8px 0 22px;
      font-size: 20px;
      color: #63656e;
    }
  }

  .permission-list {
    margin-bottom: 26px;

    table {
      width: 100%;
      border: 1px solid #dfe0e5;
    }

    th,
    td {
      height: 40px;
      padding: 0 16px;
      font-size: 14px;
      font-weight: normal;
      line-height: 40px;
      color: #575961;
      text-align: left;
      border-bottom: 1px solid #dfe0e5;
    }

    th {
      background: #fafbfd;
    }
  }

  .permission-list-empty {
    display: flex;
    height: 40px;
    align-items: center;
    justify-content: center;
    border: 1px solid #dfe0e5;
    border-top: none;
  }
</style>
