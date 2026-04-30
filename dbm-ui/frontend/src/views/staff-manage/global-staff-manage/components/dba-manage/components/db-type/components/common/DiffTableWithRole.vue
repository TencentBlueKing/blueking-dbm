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
  <div class="preview-diff-with-role mt-24">
    <div class="diff-title">
      {{ t('影响预览') }}
    </div>
    <PrimaryTable
      bordered
      class="diff-table mt-12"
      :data="data"
      :row-class-name="rowClassName"
      row-key="rowKey"
      :rowspan-and-colspan="rowspanAndColspan">
      <TableColumn
        col-key="bizName"
        :title="t('业务')">
        <template #default="{ row }: { row: IDataRow }">
          <div style="font-weight: bolder">{{ row.bizName }}</div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="privilegeDisplay"
        :title="t('修改项')"
        :width="150">
        <template #default="{ row }: { row: IDataRow }">
          <div
            class="role-dot ml-8 mr-8"
            :class="[`role-${dbaRoleTypesInfo[row.role].tagTheme}`]" />
          <span>{{ dbaRoleTypesInfo[row.role].text }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="before"
        :title="t('修改前')">
        <template #default="{ row }: { row: IDataRow }">
          <div v-if="row.before.length">
            <div
              v-for="(item, index) in row.before"
              :key="index">
              {{ `${item}（${userDataMap[item]}）` }}
            </div>
          </div>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="after"
        :title="t('修改后')">
        <template #default="{ row }: { row: IDataRow }">
          <div
            v-if="row.after.length"
            class="after-content">
            <div>
              <div
                v-for="(item, index) in row.after"
                :key="index">
                {{ `${item}（${userDataMap[item]}）` }}
              </div>
            </div>
            <BkTag
              v-if="!row.isChanged"
              class="ml-4"
              size="small">
              {{ t('无变化') }}
            </BkTag>
          </div>
          <span v-else>--</span>
        </template>
      </TableColumn>
    </PrimaryTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBARoleTypes, dbaRoleTypesInfo } from '@common/const';

  interface IDataRow {
    after: string[];
    before: string[];
    bizId: number;
    bizName: string;
    isChanged: boolean;
    role: DBARoleTypes;
    rowKey: string;
  }

  interface Props {
    data: IDataRow[];
    userDataMap: Record<string, string>;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const rowClassName = ({ row }: { row: IDataRow; rowIndex: number }) => {
    const classList: string[] = [];

    if (row.isChanged) {
      classList.push('changed-row');
    }

    return classList.join(' ');
  };

  const rowspanAndColspan = ({ colIndex, rowIndex }: { colIndex: number; rowIndex: number }) => {
    if (colIndex === 0 && rowIndex % 3 === 0) {
      return {
        rowspan: 3,
      };
    }
    return {};
  };
</script>

<style lang="less">
  .preview-diff-with-role {
    // padding: 18px 24px;

    .diff-title {
      font-weight: bolder;
      color: #313238;
    }

    .diff-table {
      .changed-row > td:last-child {
        background-color: #fdf4e8;
      }

      .role-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        vertical-align: middle;
        border-radius: 2px;
      }

      .role-info {
        background: #3a84ff;
      }

      .role-success {
        background: #2caf5e;
      }

      .role-warning {
        background: #f59500;
      }

      .before-content,
      .after-content {
        display: flex;
        align-items: baseline;
      }
    }
  }
</style>
