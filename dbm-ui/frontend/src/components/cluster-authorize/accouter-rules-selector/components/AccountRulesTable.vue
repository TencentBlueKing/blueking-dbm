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
  <div class="mongo-permission">
    <BkLoading
      :loading="loading"
      style="height: 100%">
      <DbOriginalTable
        class="mongo-permission-table"
        :columns="columns"
        :data="tableList"
        row-hover="auto"
        @clear-search="handleClearSearch" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbPermissonAccountModel from '@services/model/mongodb-permission/mongodb-permission-account';
  import { getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';

  import { AccountTypes } from '@common/const';

  interface Props {
    selectMode?: boolean,
    selectedList?: MongodbPermissonAccountModel[]
  }

  interface Emits {
    (e: 'change', value: UnwrapRef<typeof selectedMap>): void,
    (e: 'delete', value: MongodbPermissonAccountModel[]): void
  }

  interface Expose {
    searchData: (value?: Record<string, string>) => void
  }

  const props = withDefaults(defineProps<Props>(), {
    selectMode: false,
    selectedList: () => [],
  });
  const emits = defineEmits<Emits>();

  const renderList = (row: MongodbPermissonAccountModel) => (
    expandMap.value[row.account.account_id]
      ? row.rules.slice(0, 1)
      : row.rules
  );

  const { t } = useI18n();
  const router = useRouter();

  const selectedMap = shallowRef<Record<string, {
    account: MongodbPermissonAccountModel['account'],
    rule: MongodbPermissonAccountModel['rules'][number]
  }>>({});
  const expandMap = ref<Record<number, boolean>>({});

  const columns = computed(() => {
    const baseColumns = [
      {
        label: t('账号名称'),
        field: 'user',
        showOverflowTooltip: false,
        render: ({ data }: { data: MongodbPermissonAccountModel }) => (
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
        render: ({ data, index }: { data: MongodbPermissonAccountModel, index: number }) => {
          if (data.rules.length === 0) {
            return (
            <div class="mongo-permission-cell access-db">
              {
                props.selectMode && (
                  <bk-checkbox
                    disabled={true}
                    label={true}
                  />
                )
              }
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
                {
                  props.selectMode && (
                    <bk-checkbox
                      model-value={Boolean(selectedDomainMap.value[rule.rule_id])}
                      label={true}
                      onChange={() => handleChange(index, ruleIndex)}
                    />
                  )
                }
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
        render: ({ data, index }: { data: MongodbPermissonAccountModel, index: number }) => {
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
    const operationColumn = {
      label: t('操作'),
      width: 100,
      render: ({ data, index }: { data: MongodbPermissonAccountModel, index: number }) => (
        renderList(data).map((rule, ruleIndex) => (
          <div class="mongo-permission-cell">
            <bk-button
              theme="primary"
              text
              onClick={ () => handleDelete(index, ruleIndex) }>
              { t('删除') }
            </bk-button>
          </div>
        ))
      ),
    };

    if (props.selectMode) {
      return baseColumns;
    }

    return [...baseColumns, operationColumn];
  });

  const tableList = computed(() => {
    if (props.selectMode) {
      return ruleList.value?.results || [];
    }
    return _.cloneDeep(props.selectedList);
  });

  const {
    data: ruleList,
    run: getMongodbPermissionRulesRun,
    loading,
  } = useRequest(getMongodbPermissionRules, {
    manual: true,
    onSuccess() {
      expandMap.value = {};
    },
  });

  watch(() => props.selectedList, (newDataList) => {
    if (props.selectMode) {
      const newDataListCopy = _.cloneDeep(newDataList);
      selectedMap.value = newDataListCopy.reduce((prevSelectedMap, dataItem) => {
        const ruleMap = dataItem.rules
          .reduce((prevRuleMap, ruleItem) => Object.assign({}, prevRuleMap, {
            [ruleItem.rule_id]: Object.assign({}, dataItem, { rule: ruleItem }),
          }), {} as typeof selectedMap.value);
        return Object.assign({}, prevSelectedMap, ruleMap);
      }, {});
      emits('change', selectedMap.value);
    }
  }, {
    immediate: true,
  });

  const getList = (searchSelectorParams: object = {}) => {
    getMongodbPermissionRulesRun({
      ...searchSelectorParams,
      account_type: AccountTypes.MONGODB,
    });
  };

  const handleClearSearch = () => {
    getList();
  };

  const handleToggleExpand = (data: MongodbPermissonAccountModel) => {
    // 长度小于等于 1 则没有展开收起功能
    if (data.rules.length <= 1) {
      return;
    }
    expandMap.value[data.account.account_id] = !expandMap.value[data.account.account_id];
  };

  const handleShowCreateRule = (row: MongodbPermissonAccountModel, event: Event) => {
    event.stopPropagation();
    const route = router.resolve({
      name: 'MongodbPermission',
    });
    window.open(route.href);
  };

  // 选中域名列表
  const selectedDomainMap = computed(() => Object.keys(selectedMap.value)
    .reduce((result, selectKey) => Object.assign({}, result, { [selectKey]: true }), {} as Record<number, boolean>));

  const handleChange = (dataIndex: number, ruleIndex: number) => {
    if (!props.selectMode) {
      return;
    }
    const rowItem = ruleList.value!.results[dataIndex];
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

  const handleDelete = (index: number, ruleIndex: number) => {
    const dataListCopy = _.cloneDeep(props.selectedList);
    dataListCopy[index].rules.splice(ruleIndex, 1);

    if (dataListCopy[index].rules.length === 0) {
      dataListCopy.splice(index, 1);
    }
    emits('delete', dataListCopy);
  };

  defineExpose<Expose>({
    searchData(searchSelectorParams: Record<string, string> = {}) {
      if (props.selectMode) {
        getList(searchSelectorParams);
      }
    },
  });
</script>

<style lang="less" scoped>
.mongo-permission {
  height: calc(100% - 48px);

  .mongo-permission-operations {
    display: flex;
    padding-bottom: 16px;
    justify-content: space-between;
    align-items: center;
  }

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
    color: #63656E;
    cursor: pointer;
    align-items: center;
  }

  :deep(.user-name-text) {
    margin-right: 16px;
    font-weight: bold;
  }
}

:deep(.mongo-permission-table) {
  height: 100% !important;
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
