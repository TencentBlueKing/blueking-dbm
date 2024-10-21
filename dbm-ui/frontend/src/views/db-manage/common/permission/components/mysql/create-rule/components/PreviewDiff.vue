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
  <div class="preview-diff">
    <div>
      <span class="preview-diff-title mr-7">{{ t('请确认以下差异变化：') }}</span>
      <span
        v-for="(tag, index) in tags"
        :key="tag.type"
        :class="[`tag-${tag.type}`, { 'ml-25': index > 0 }]">
        {{ tag.text }}
      </span>
    </div>
    <DbCard
      v-model:collapse="collapseActive.accessDb"
      class="mt-16"
      :is-active="collapseActive.accessDb"
      mode="collapse"
      :title="t('访问DB')">
      <BkTable
        :border="['col', 'outer']"
        :columns="accessColumns"
        :data="accessDbData" />
    </DbCard>
    <DbCard
      v-model:collapse="collapseActive.privilege"
      class="mt-26 privilege-card"
      :is-active="collapseActive.privilege"
      mode="collapse">
      <template #desc>
        <I18nT
          class="privilege-table-title"
          keypath="权限：新增n个，删除m个"
          tag="span">
          <span style="color: #2dcb56">{{ addCount }}</span>
          <span style="color: #ea3636">{{ deleteCount }}</span>
        </I18nT>
      </template>
      <BkTable
        :border="['col', 'outer']"
        :cell-class="getCellClass"
        class="privilege-table"
        :columns="privilegeColumns"
        :data="privilegeData"
        row-key="diffType" />
    </DbCard>
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import type { AccountRule, AccountRulePrivilege, AccountRulePrivilegeKey } from '@services/types';

  interface PrivilegeRow {
    privilegeKey: string;
    privilegeDisplay: string;
    beforePrivilege: string;
    afterPrivilege: string;
    // 差异类型
    diffType: 'add' | 'delete' | 'unchanged';
    // 是否敏感词
    isSensitiveWord: boolean;
  }

  interface Props {
    ruleSettingsConfig: {
      dbOperations: AccountRulePrivilege,
      ddlSensitiveWords: string[],
    };
    rulesFormData: {
      beforeChange: AccountRule;
      afterChange: AccountRule;
    }
  }

  interface Exposes {
    changed: {
      accessDb: boolean;
      privilege: {
        addCount: number;
        deleteCount: number;
      };
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const collapseActive = reactive({
    accessDb: true,
    privilege: true,
  });

  const accessDbData = computed(() => [
    {
      oldAccessDb: props.rulesFormData.beforeChange?.access_db || '--',
      newAccessDb: props.rulesFormData.afterChange?.access_db || '--',
    },
  ]);

  const diffArray = (oldArray: string[], newArray: string[]) => {
    const diffMap: Record<string, PrivilegeRow['diffType']> = Object.fromEntries(
      oldArray.map(item => [item, 'delete'])
    );
    newArray.forEach(item => {
      diffMap[item] = diffMap[item] ? 'unchanged' : 'add';
    });
    return diffMap;
  }

  const getSensitiveWordMap = () => Object.fromEntries(
    (props.ruleSettingsConfig.ddlSensitiveWords || []).map(word => [word, true])
  );

  const getPrivilegeData = (key: AccountRulePrivilegeKey) => {
    const beforeList = props.rulesFormData.beforeChange?.privilege[key] || [];
    const afterList = props.rulesFormData.afterChange?.privilege[key] || [];
    const diffMap = diffArray(beforeList, afterList);
    const sensitiveWordMap = getSensitiveWordMap();
    return Object.entries(diffMap).reduce<PrivilegeRow[]>((acc, [privilege, diffType]) => [...acc, {
      privilegeKey: key,
      privilegeDisplay: key === 'glob' ? t('全局') : key.toUpperCase(),
      beforePrivilege: diffType === 'add' ? '' : privilege,
      afterPrivilege: privilege,
      diffType,
      isSensitiveWord: key === 'glob' || sensitiveWordMap[privilege],
    }], [])
  };

  const privilegeData = computed(() => [
    ...getPrivilegeData('dml'),
    ...getPrivilegeData('ddl'),
    ...getPrivilegeData('glob'),
  ]);

  const addCount = computed(() => privilegeData.value.filter(item => item.diffType === 'add').length);
  const deleteCount = computed(() => privilegeData.value.filter(item => item.diffType === 'delete').length);

  const tags: {
    type: PrivilegeRow['diffType'],
    text: string
  }[] = [
      {
        type: 'add',
        text: t('新增'),
      },
      {
        type: 'delete',
        text: t('删除'),
      },
      {
        type: 'unchanged',
        text: t('不变'),
      },
    ];
  const accessColumns: Column[] = [
    {
      label: t('变更前'),
      field: 'oldAccessDb',
      width: 300,
    },
    {
      label: t('变更后'),
      field: 'newAccessDb',
      width: 300,
    },
  ];
  const privilegeColumns: Column[] = [
    {
      label: t('权限类型'),
      field: 'privilegeDisplay',
      width: 200,
      rowspan: ({ row }: { row: PrivilegeRow }) => {
        const { privilegeKey } = row;
        const rowSpan = privilegeData.value.filter((item) => item.privilegeKey === privilegeKey).length;
        return rowSpan > 1 ? rowSpan : 1;
      },
      render: ({ row }: { row: PrivilegeRow }) => <span class="cell-bold">{row.privilegeDisplay}</span>
    },
    {
      label: t('变更前'),
      field: 'beforePrivilege',
      width: 200,
      render: ({ row }: { row: PrivilegeRow }) => {
        const { beforePrivilege, isSensitiveWord } = row;
        return beforePrivilege ? (
          <div>
            <span>{beforePrivilege}</span>
            {
              isSensitiveWord && <span class="sensitive-tip">{t('敏感')}</span>
            }
          </div>
        ) : '--'
      }
    },
    {
      label: t('变更后'),
      field: 'afterPrivilege',
      width: 200,
      render: ({ row }: { row: PrivilegeRow }) => {
        const { afterPrivilege, isSensitiveWord } = row;
        return (
          <div>
            <span>{afterPrivilege}</span>
            {
              isSensitiveWord && <span class="sensitive-tip">{t('敏感')}</span>
            }
          </div>
        )
      }
    },
  ];

  const getCellClass = (data: { field: string }) => data.field === 'afterPrivilege' ? 'cell-privilege' : '';

  defineExpose<Exposes>({
    changed: {
      accessDb: accessDbData.value[0].newAccessDb!== accessDbData.value[0].oldAccessDb,
      privilege: {
        addCount: addCount.value,
        deleteCount: deleteCount.value,
      }
    }
  })
</script>

<style lang="less" scoped>
  :deep(.bk-scrollbar-wrapper .bk-scrollbar-content-el) {
    display: flex;
  }

  .preview-diff {
    padding: 18px 24px;

    .preview-diff-title {
      font-size: 14px;
      font-weight: 700;
      color: #63656e;
    }

    .tag-add::before {
      position: relative;
      top: 2px;
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 5px;
      background: #f2fff4;
      border: 1px solid #b3ffc1;
      content: '';
    }

    .tag-delete::before {
      position: relative;
      top: 2px;
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 5px;
      background: #ffeded;
      border: 1px solid #ffd2d2;
      content: '';
    }

    .tag-unchanged::before {
      position: relative;
      top: 2px;
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 5px;
      background: #fff;
      border: 1px solid #c4c6cc;
      content: '';
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
        padding-top: 0;
      }

      .privilege-table-title {
        font-weight: bold;
        color: #313238;
        flex-shrink: 0;
      }

      .privilege-table {
        height: calc(100vh - 400px) !important;

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

        .cell-privilege {
          .cell {
            padding: 0;

            div {
              padding-left: 16px;
            }
          }
        }

        .cell-privilege[data-id^='add_'] {
          background-color: #f2fff4;
        }

        .cell-privilege[data-id^='delete_'] {
          background-color: #ffeeeee6;

          .cell {
            color: #f8b4b4;
            text-decoration: line-through;
          }
        }
      }
    }
  }

  :deep(.db-card[is-active='false'] .db-card__header) {
    border: 1px solid var(--table-border-color);
  }
</style>
