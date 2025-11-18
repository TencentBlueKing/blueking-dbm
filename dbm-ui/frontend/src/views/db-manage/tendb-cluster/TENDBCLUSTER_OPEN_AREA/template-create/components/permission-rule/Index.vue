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
  <div>
    <BkButton
      v-bk-tooltips="{
        content: t('请先选择源集群'),
        disabled: !!sourceClusterId,
        placement: 'top',
      }"
      class="mb-12"
      :disabled="!sourceClusterId"
      @click="handleShow">
      <DbIcon
        style="margin-right: 3px"
        type="add" />
      <span>{{ t('添加权限') }}</span>
    </BkButton>
    <BKLoading :loading="loading">
      <BkTable
        v-if="tableData.length > 0"
        class="openarea-permission-rule-table"
        :data="tableData"
        :row-class-name="rowClass"
        :show-overflow="false">
        <BkTableColumn
          field="user"
          :label="t('账号名称')"
          :width="220">
          <template #default="{ row }: { row: MysqlPermissionAccountModel }">
            <DbIcon
              v-if="row.rules.length > 1"
              class="flod-flag"
              :class="{
                'is-flod': rowFlodMap[row.account.user],
              }"
              type="down-shape"
              @click="() => handleToogleExpand(row.account.user)" />
            {{ row.account.user }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="access_db"
          :label="t('访问DB')"
          :width="300">
          <template #default="{ row }: { row: MysqlPermissionAccountModel }">
            <p
              v-for="item in rowFlodMap[row.account.user] ? row.rules : row.rules.slice(0, 1)"
              :key="item.rule_id"
              class="inner-row">
              <BkTag>{{ item.access_db }}</BkTag>
            </p>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="privilege"
          :label="t('权限')"
          :min-width="300">
          <template #default="{ row }: { row: MysqlPermissionAccountModel }">
            <TextOverflowLayout
              v-for="item in rowFlodMap[row.account.user] ? row.rules : row.rules.slice(0, 1)"
              :key="item.rule_id"
              class="inner-row">
              {{ item.privilege }}
            </TextOverflowLayout>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="operate"
          :label="t('操作')"
          :min-width="145">
          <template #default="{ row }: { row: MysqlPermissionAccountModel }">
            <p
              v-for="item in rowFlodMap[row.account.user] ? row.rules : row.rules.slice(0, 1)"
              :key="item.rule_id">
              <BkButton
                text
                theme="primary"
                @click="handleRemove(item)">
                {{ t('移除') }}
              </BkButton>
            </p>
          </template>
        </BkTableColumn>
      </BkTable>
    </BKLoading>
    <PermissionRuleSelector
      v-model="permissionRules"
      v-model:is-show="isShowPermissionRule"
      :account-type="AccountTypes.TENDBCLUSTER"
      :cluster-id="sourceClusterId"
      @submit="handleSelected" />
  </div>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MysqlPermissionAccountModel from '@services/model/mysql/mysql-permission-account';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount';

  import { AccountTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import PermissionRuleSelector from './components/PermissionRuleSelector.vue';

  const sourceClusterId = defineModel<number>('sourceClusterId', {
    required: true,
  });

  const permissionRules = defineModel<number[]>({
    required: true,
  });

  const { t } = useI18n();

  const isShowPermissionRule = ref(false);
  const rowFlodMap = ref<Record<string, boolean>>({});
  const tableData = ref<MysqlPermissionAccountModel[]>([]);

  const { loading, run: fetchData } = useRequest(getPermissionRules, {
    manual: true,
    onSuccess(data) {
      tableData.value = data.results;
    },
  });

  const handleShow = () => {
    isShowPermissionRule.value = true;
  };

  const handleSelected = async (ruleIds: number[]) => {
    if (ruleIds.length === 0) {
      return;
    }
    fetchData({
      account_type: AccountTypes.TENDBCLUSTER,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      limit: -1,
      offset: 0,
      rule_ids: ruleIds.join(','),
    });
  };

  const rowClass = ({ row }: { row: MysqlPermissionAccountModel }) => {
    if (!rowFlodMap.value[row.account.user]) {
      return 'init-height';
    }
    return '';
  };

  const handleToogleExpand = (user: string) => {
    if (rowFlodMap.value[user]) {
      delete rowFlodMap.value[user];
    } else {
      rowFlodMap.value[user] = true;
    }
  };

  const handleRemove = (data: MysqlPermissionAccountModel['rules'][number]) => {
    const permission = tableData.value.find((item) => item.account.account_id === data.account_id);
    if (!permission) return;

    permission.rules = permission.rules.filter((item) => item.rule_id !== data.rule_id);
    if (!permission.rules.length) {
      tableData.value = tableData.value.filter((item) => item !== permission);
    }

    permissionRules.value = permissionRules.value.filter((id) => id !== data.rule_id);
  };

  watch(permissionRules, () => {
    handleSelected(permissionRules.value);
  });

  defineExpose({
    reset() {
      tableData.value = [];
      permissionRules.value = [];
    },
  });
</script>
<style lang="less">
  .openarea-permission-rule-table {
    .flod-flag {
      display: inline-block;
      margin-right: 4px;
      cursor: pointer;
      transition: all 0.1s;

      &.is-flod {
        transform: rotateZ(-90deg);
      }
    }

    .inner-row {
      height: 28px;
      display: flex;
      align-items: center;
    }

    .init-height {
      td {
        height: initial !important;
      }
    }
  }
</style>
