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
  <InfoList>
    <InfoItem :label="t('变更类型')">
      {{ t('变更规则') }}
    </InfoItem>
    <InfoItem :label="t('账户名称')">
      {{ ticketDetails.details.last_account_rules.userName }}
    </InfoItem>
  </InfoList>
  <div class="preview-diff">
    <DbCard
      v-model:collapse="collapseActive.accessDb"
      :is-active="collapseActive.accessDb"
      mode="collapse"
      :title="t('访问DB变更前后对比')">
      <BkTable :data="accessDbData">
        <BkTableColumn
          field="oldAccessDb"
          :label="t('变更前')" />
        <BkTableColumn
          field="newAccessDb"
          :label="t('变更后')" />
      </BkTable>
    </DbCard>
    <DbCard
      v-model:collapse="collapseActive.privilege"
      class="mt-26 privilege-card"
      :is-active="collapseActive.privilege"
      mode="collapse">
      <template #desc>
        <I18nT
          class="privilege-table-title"
          keypath="权限变更前后对比：新增n个，删除m个"
          scope="global">
          <span style="color: #2dcb56">{{ addCount }}</span>
          <span style="color: #ea3636">{{ deleteCount }}</span>
        </I18nT>
      </template>
      <BkTable
        class="privilege-table"
        :data="privilegeData"
        :merge-cells="mergeCells">
        <BkTableColumn
          class-name="cell-bold"
          field="privilegeDisplay"
          :label="t('权限类型')" />
        <BkTableColumn :label="t('变更前')">
          <template #default="{ data }: { data: PrivilegeRow }">
            <div v-if="data.beforePrivilege">
              <span>{{ data.beforePrivilege }}</span>
              <span
                v-if="data.isSensitiveWord"
                class="sensitive-tip">
                {{ t('敏感') }}
              </span>
            </div>
            <span v-else>--</span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          class-name="cell-privilege"
          :label="t('变更后')">
          <template #default="{ data }: { data: PrivilegeRow }">
            <div
              v-if="data.afterPrivilege"
              :class="[data.diffType]">
              <span>{{ data.afterPrivilege }}</span>
              <span
                v-if="data.isSensitiveWord"
                class="sensitive-tip">
                {{ t('敏感') }}
              </span>
            </div>
            <span v-else>--</span>
          </template>
        </BkTableColumn>
      </BkTable>
    </DbCard>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import type { AccountRule, AccountRulePrivilegeKey } from '@services/types';

  import { AccountTypes } from '@common/const';

  import configMap from '@views/db-manage/common/permission/components/mysql/config';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  interface PrivilegeRow {
    afterPrivilege: string;
    beforePrivilege: string;
    // 差异类型
    diffType: 'add' | 'delete' | 'unchanged';
    // 是否敏感词
    isSensitiveWord: boolean;
    privilegeDisplay: string;
    privilegeKey: string;
  }

  interface Props {
    accountType?: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
    ticketDetails: TicketModel<Mysql.AccountRuleChange>;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountType: AccountTypes.MYSQL,
  });

  const { t } = useI18n();

  const collapseActive = reactive({
    accessDb: true,
    privilege: true,
  });
  const rulesFormData = reactive({
    afterChange: {} as AccountRule,
    beforeChange: {} as AccountRule,
  });
  const privilegeData = shallowRef<PrivilegeRow[]>([]);
  const mergeCells = shallowRef<Array<{ col: number; colspan: number; row: number; rowspan: number }>>([]);

  const accessDbData = computed(() => [
    {
      newAccessDb: rulesFormData.afterChange.access_db || '--',
      oldAccessDb: rulesFormData.beforeChange.access_db || '--',
    },
  ]);
  const addCount = computed(() => privilegeData.value.filter((item) => item.diffType === 'add').length);
  const deleteCount = computed(() => privilegeData.value.filter((item) => item.diffType === 'delete').length);

  const diffArray = (oldArray: string[], newArray: string[]) => {
    const diffMap: Record<string, PrivilegeRow['diffType']> = Object.fromEntries(
      oldArray.map((item) => [item, 'delete']),
    );
    newArray.forEach((item) => {
      diffMap[item] = diffMap[item] ? 'unchanged' : 'add';
    });
    return diffMap;
  };

  const getSensitiveWordMap = () =>
    Object.fromEntries((configMap[props.accountType]?.ddlSensitiveWords || []).map((word) => [word, true]));

  const getPrivilegeData = (key: AccountRulePrivilegeKey) => {
    const beforeList = rulesFormData.beforeChange.privilege[key] || [];
    const afterList = rulesFormData.afterChange.privilege[key] || [];
    const diffMap = diffArray(beforeList, afterList);
    const sensitiveWordMap = getSensitiveWordMap();
    return Object.entries(diffMap).reduce<PrivilegeRow[]>(
      (acc, [privilege, diffType]) => [
        ...acc,
        {
          afterPrivilege: privilege,
          beforePrivilege: diffType === 'add' ? '' : privilege,
          diffType,
          isSensitiveWord: key === 'glob' || sensitiveWordMap[privilege],
          privilegeDisplay: key === 'glob' ? t('全局') : key.toUpperCase(),
          privilegeKey: key,
        },
      ],
      [],
    );
  };

  watch(
    () => props.ticketDetails,
    () => {
      const {
        access_db: accessDb,
        account_id: accountId,
        last_account_rules: lastAccountRules,
        privilege,
      } = props.ticketDetails.details;
      rulesFormData.beforeChange = lastAccountRules;
      rulesFormData.afterChange = {
        access_db: accessDb,
        account_id: accountId,
        privilege,
      };
    },
    {
      immediate: true,
    },
  );

  watchEffect(() => {
    const dmlData = getPrivilegeData('dml');
    const ddlData = getPrivilegeData('ddl');
    const globData = getPrivilegeData('glob');
    mergeCells.value = [
      {
        col: 0,
        colspan: 1,
        row: 0,
        rowspan: dmlData.length,
      },
      {
        col: 0,
        colspan: 1,
        row: dmlData.length,
        rowspan: ddlData.length,
      },
      {
        col: 0,
        colspan: 1,
        row: dmlData.length + ddlData.length,
        rowspan: globData.length,
      },
    ];
    privilegeData.value = [...dmlData, ...ddlData, ...globData];
  });
</script>

<style lang="less" scoped>
  .preview-diff {
    .preview-diff-title {
      font-size: 14px;
      font-weight: 700;
      color: #63656e;
    }

    .privilege-card {
      :deep(.db-card__title) {
        display: none;
      }
    }

    :deep(.db-card) {
      padding: 0;

      .db-card__header {
        height: 35px;
        padding: 24px 12px;
        background-color: #fafbfd;
        border-top: 1px solid var(--table-border-color);
        border-right: 1px solid var(--table-border-color);
        border-left: 1px solid var(--table-border-color);
      }

      .db-card__content {
        padding: 0;
      }

      .privilege-table-title {
        font-weight: bold;
        color: #313238;
        flex-shrink: 0;
      }

      .privilege-table {
        .cell-bold {
          font-weight: 700;
        }

        .sensitive-tip {
          height: 16px;
          padding: 0 4px;
          margin-left: 8px;
          font-size: 10px;
          line-height: 16px;
          color: #fe9c00;
          text-align: center;
          background: #fff3e1;
          border-radius: 2px;
        }

        .cell-privilege:has(.vxe-cell .add) {
          background-color: #f2fff4;
        }

        .cell-privilege:has(.vxe-cell .delete) {
          color: #f8b4b4;
          text-decoration: line-through;
          background-color: #ffeeeee6;
        }
      }
    }
  }

  :deep(.db-card[is-active='false'] .db-card__header) {
    border: 1px solid var(--table-border-color);
  }
</style>
