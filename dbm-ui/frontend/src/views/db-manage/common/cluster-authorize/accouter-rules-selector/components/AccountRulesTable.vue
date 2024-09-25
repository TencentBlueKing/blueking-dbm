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
  <DbTable
    ref="tableRef"
    class="mongo-permission-table"
    :columns="columns"
    :data-source="dataSource"
    :max-height="700"
    row-hover="auto"
    @clear-search="handleClearSearch" />
</template>

<script setup lang="tsx" generic="T extends MongodbPermissonAccountModel | SqlserverPermissionAccountModel">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MongodbPermissonAccountModel from '@services/model/mongodb/mongodb-permission-account';
  import SqlserverPermissionAccountModel from '@services/model/sqlserver/sqlserver-permission-account';
  import { getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';

  import { AccountTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';

  interface Props {
    accountType: string,
    selectedList?: T[]
  }

  interface Emits {
    (e: 'change', value: UnwrapRef<typeof selectedMap>): void,
    (e: 'delete', value: T[]): void
  }

  interface Expose {
    searchData: (value?: Record<string, string>) => void
  }

  const props = withDefaults(defineProps<Props>(), {
    selectMode: false,
    selectedList: () => [],
  });
  const emits = defineEmits<Emits>();

  const renderList = (row: T) => (
    expandMap.value[row.account.account_id]
      ? row.rules.slice(0, 1)
      : row.rules
  );

  const { t } = useI18n();
  const router = useRouter();

  const selectedMap = shallowRef<Record<string, {
    account: T['account'],
    rule: T['rules'][number]
  }>>({});
  const expandMap = ref<Record<number, boolean>>({});
  const tableRef = ref<InstanceType<typeof DbTable>>()

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: T }) => (
          <div
            class="mongo-permission-cell"
            onClick={ () => handleToggleExpand(data) }>
            {
              data.rules.length > 1 && (
                <db-icon
                  type="down-shape"
                  class={[
                    'user-icon',
                    { 'user-icon-expand': !expandMap.value[data.account.account_id] },
                  ]} />
              )
            }
            {
              <div class="user-name">
                { data.account.user }
              </div>
            }
            {
              data.isNew && (
                <span
                  class="glob-new-tag ml-6"
                  data-text="NEW" />
              )
            }
          </div>
        ),
    },
    {
      label: t('访问DB'),
      field: 'access_db',
      showOverflowTooltip: true,
      render: ({ data, index }: { data: T, index: number }) => {
        if (data.rules.length === 0) {
          return (
            <div class="mongo-permission-cell access-db">
              <bk-checkbox
                disabled={true}
                label={true}
              />
              <span>{ t('暂无规则') }，</span>
              <bk-button
                theme="primary"
                size="small"
                text
                onClick={ (event: Event) => handleShowCreateRule(data, event) }>
                { t('立即新建') }
              </bk-button>
            </div>
          );
        }

        return (
          renderList(data).map((rule, ruleIndex) => (
              <div
                class="mongo-permission-cell access-db"
                onClick={() => handleChange(index, ruleIndex)}>
                <bk-checkbox
                  model-value={Boolean(selectedDomainMap.value[rule.rule_id])}
                  label={true}
                  onChange={() => handleChange(index, ruleIndex)}
                />
                <bk-tag>{ rule.access_db }</bk-tag>
              </div>
          ))
        );
      },
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: false,
      render: ({ data, index }: { data: T, index: number }) => {
        if (data.rules.length > 0) {
          return renderList(data).map((rule, ruleIndex) => {
            const { privilege } = rule;

            return (
              <div
                class="mongo-permission-cell"
                onClick={() => handleChange(index, ruleIndex)}>
                {
                  privilege ? privilege.replace(/,/g, '，') : '--'
                }
              </div>
            );
          });
        }

        return <div class="mongo-permission-cell">--</div>;
      },
    },
  ];

  const dataSource = computed(() => {
    const apiMap: Record<string, (params: any) => Promise<any>> = {
      [AccountTypes.MONGODB]: getMongodbPermissionRules,
      [AccountTypes.SQLSERVER]: getSqlserverPermissionRules
    }

    return apiMap[props.accountType]
  })

  watch(() => props.selectedList, (newDataList) => {
    const newDataListCopy = _.cloneDeep(newDataList);
    selectedMap.value = newDataListCopy.reduce((prevSelectedMap, dataItem) => {
      const ruleMap = dataItem.rules
        .reduce((prevRuleMap, ruleItem) => Object.assign({}, prevRuleMap, {
          [ruleItem.rule_id]: Object.assign({}, dataItem, { rule: ruleItem }),
        }), {} as typeof selectedMap.value);
      return Object.assign({}, prevSelectedMap, ruleMap);
    }, {});
    emits('change', selectedMap.value);
  }, {
    immediate: true,
  });

  const getList = (searchSelectorParams: Record<string, string> = {}) => {
    tableRef.value!.fetchData({
      ...searchSelectorParams,
    }, {
      account_type: props.accountType,
    })
  };

  const handleClearSearch = () => {
    getList();
  };

  const handleToggleExpand = (data: T) => {
    // 长度小于等于 1 则没有展开收起功能
    if (data.rules.length <= 1) {
      return;
    }
    expandMap.value[data.account.account_id] = !expandMap.value[data.account.account_id];
  };

  const handleShowCreateRule = (row: T, event: Event) => {
    event.stopPropagation();
    const routeMap: Record<string, string> = {
      [AccountTypes.MONGODB]: 'MongodbPermission',
      [AccountTypes.SQLSERVER]: 'SqlServerPermissionRules'
    }
    const route = router.resolve({
      name: routeMap[props.accountType],
    });
    window.open(route.href);
  };

  // 选中域名列表
  const selectedDomainMap = computed(() => Object.keys(selectedMap.value)
    .reduce((result, selectKey) => Object.assign({}, result, { [selectKey]: true }), {} as Record<number, boolean>));

  const handleChange = (dataIndex: number, ruleIndex: number) => {
    const rowItem = tableRef.value!.getData<T>()[dataIndex]
    const ruleItem = rowItem.rules[ruleIndex];
    const isChecked = !!(selectedMap.value[ruleItem.rule_id]);
    const selectedMapMemo = { ...selectedMap.value };
    if (!isChecked) {
      selectedMapMemo[ruleItem.rule_id] = Object.assign({}, rowItem, { rule: ruleItem });
    } else {
      delete selectedMapMemo[ruleItem.rule_id];
    }
    selectedMap.value = selectedMapMemo;
    emits('change', selectedMapMemo);
  };

  defineExpose<Expose>({
    searchData(searchSelectorParams: Record<string, string> = {}) {
      getList(searchSelectorParams);
    },
  });
</script>

<style lang="less" scoped>
  :deep(.mongo-permission-cell) {
    position: relative;
    padding: 0 15px;
    overflow: hidden;
    line-height: calc(var(--row-height) - 1px);
    text-overflow: ellipsis;
    white-space: nowrap;
    border-bottom: 1px solid @border-disable;
  }

  :deep(.access-db) {
    display: flex;
    align-items: center;
    height: 42px;
  }

  :deep(.mongo-permission-cell:last-child) {
    border-bottom: 0;
  }

  :deep(.user-icon) {
    position: absolute;
    top: 50%;
    left: 15px;
    transform: translateY(-50%) rotate(-90deg);
    transition: all 0.2s;
  }

  :deep(.user-icon-expand) {
    transform: translateY(-50%) rotate(0);
  }

  :deep(.user-name) {
    display: flex;
    height: 100%;
    padding-left: 24px;
    font-weight: 700;
    color: #63656e;
    cursor: pointer;
    align-items: center;
  }

  :deep(.user-name-text) {
    margin-right: 16px;
    font-weight: bold;
  }

  :deep(.mongo-permission-table) {
    // height: 100% !important;
    transition: all 0.5s;

    td {
      .cell {
        padding: 0 !important;
      }
    }

    td:first-child {
      .cell,
      .mongo-permission-cell {
        // height: 100% !important;
        height: calc(var(--row-height) - 1px);
      }
    }
  }
</style>
