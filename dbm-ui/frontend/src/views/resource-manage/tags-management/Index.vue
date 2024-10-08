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
    <Teleport to="#dbContentTitleAppend">
      <BkTag
        class="ml-8"
        theme="info">
        {{ t('全局') }}
      </BkTag>
      <span class="title-divider">|</span>
    </Teleport>
    <div class="tags-management-container">
      <div class="header-action mb-16">
        <BkButton
          class="operation-btn"
          theme="primary"
          @click="handleCreate"
          >{{ t('新建') }}</BkButton
        >
        <BkButton
          class="operation-btn"
          :disabled="!hasSelected"
          @click="handleBatchDelete"
          >{{ t('批量删除') }}</BkButton
        >
        <DbSearchSelect
          class="search-selector"
          :data="searchSelectData"
          :get-menu-list="getMenuList"
          :model-value="searchValue"
          :placeholder="t('请输入标签关键字')"
          style="width: 500px"
          unique-select
          :validate-values="validateSearchValues"
          @change="handleSearchValueChange" />
      </div>
      <div>
        <DbTable
          ref="tableRef"
          class="table-box"
          :columns="tableColumn"
          :data-source="getResourceTags"
          primary-key="tag"
          selectable
          @clear-search="clearSearchValue"
          @column-filter="columnFilterChange"
          @column-sort="columnSortChange"
          @selection="handleSelection" />
      </div>
    </div>
    <CreateTagDialog
      v-model:is-show="isCreateTagDialogShow"
      bk-biz-id="1" />
  </div>
</template>

<script setup lang="tsx">
  import { Button, InfoBox } from 'bkui-vue';
  import BKPopConfirm from 'bkui-vue/lib/pop-confirm';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import AutoFocusInput from '@views/resource-manage/tags-management/AutoFocusInput.vue'
  import CreateTagDialog from '@views/resource-manage/tags-management/CreateTagDialog.vue'

  import { ClusterTypes } from '@/common/const/clusterTypes';
  import { useCopy } from '@/hooks';
  import { useLinkQueryColumnSerach } from '@/hooks/useLinkQueryColumnSerach';
  import type ResourceTagModel from '@/services/model/db-resource/ResourceTag';
  import { deleteResourceTags, getResourceTags, modifyResourceTag } from '@/services/source/tag';
  import { getUserList } from '@/services/source/user';
  import { getMenuListSearch } from '@/utils/getMenuListSearch';

  const { t } = useI18n();
  const copy = useCopy();
  const {
    searchValue,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBHA,
    attrs: [],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const tableRef = ref();
  const selected = ref<ResourceTagModel[]>([]);
  const isCreateTagDialogShow = ref(false);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const searchSelectData = computed(() => ([
    {
      name: '标签',
      id: 'tag',
    },
    {
      name: '绑定的IP',
      id: 'boundIp',
    },
    {
      name: '创建人',
      id: 'creator',
    },
    {
      name: '创建时间',
      id: 'creationTime',
    },
  ]));

  const tableColumn = [
    {
      label: '标签',
      field: 'tag',
      render: ({ data }: { data: ResourceTagModel }) => {
        const renderTag = () => {
          if (data.is_show_edit) {
            return (
              <AutoFocusInput modelValue={data.tag} clearable={false} onBlur={async () => {
                try {
                  await modifyResourceTag(data);
                }
                finally {
                  Object.assign(data, {
                    is_show_edit: false,
                  });
                }
              }}></AutoFocusInput>
            )
          }
          return (
            <>
              <span>{data.tag}</span>
              <db-icon
                class="operation-icon"
                type="edit"
                style="font-size: 18px"
                onClick={() => {
                  Object.assign(data, {
                    is_show_edit: true,
                  });
                }} />
            </>
          )
        }
        return (
          <div class="tag-box">
            {renderTag()}
          </div>
        );
      }
    },
    {
      label: '绑定的IP',
      field: 'boundIp',
      render: ({ data }: { data: ResourceTagModel }) => (
        <div class={'ip-box'}>
          <span v-bk-tooltips={{
            content: data.boundIp.join('\n'),
            disabled: data.ipCount === 0
          }}>
            {data.ipCount}
          </span>
          <db-icon
            class="operation-icon"
            type="copy"
            style="font-size: 18px"
            onClick={() => {
              copy(data.boundIp.join('\n'));
            }} />
        </div>
      )
    },
    {
      label: '创建人',
      field: 'creator',
    },
    {
      label: '创建时间',
      field: 'creationTime',
      render: ({ data }: { data: ResourceTagModel }) => data.creationTimeDisplay,
    },
    {
      label: '操作',
      render: ({ data }: { data: ResourceTagModel }) => (
        <BKPopConfirm
          width={280}
          trigger='click'
          title={t('确认删除该标签值？')}
          onConfirm={async () => {
            await deleteResourceTags([data.id]);
            fetchData();
          }}
        >
          {{
            default: <Button theme='primary' text>删除</Button>,
            content: (
              <div>
                <div>{t('标签：')}<span style={{ color: '#313238' }}>{data.tag}</span></div>
                <div class={'mb-10 mt-4'}>{t('删除操作无法撤回，请谨慎操作！')}</div>
              </div>
            )
          }}
        </BKPopConfirm>
      )
    }
  ];

  const fetchData = () => {
    tableRef.value.fetchData();
  };

  const handleSelection = (_data: ResourceTagModel, list: ResourceTagModel[]) => {
    selected.value = list;
  };

  const handleBatchDelete = async () => {
    InfoBox({
      title: t('确认批量删除n个标签？', { n: selected.value.length }),
      confirmText: t('删除'),
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      width: 480,
      class: 'batch-delete-wrapper',
      content: (
        <div class={'batch-delete-wrapper'}>
          <div style={{
            display: 'flex'
          }}>
            <div style={{
              textAlign: 'left'
            }}>
              {t('标签:')}
            </div>
            <div style={{
              flex: 1,
              color: '#313238'
            }}>
              {
                selected.value.map(v => v.tag).join(',')
              }
            </div>
          </div>
          <div style={{
            background: '#F5F6FA',
            borderRadius: '2px',
            padding: '12px 16px',
            marginTop: '16px'
          }}>
            {
              t('删除后将无法恢复，请谨慎操作')
            }
          </div>
        </div>
      ),
      onConfirm: async () => {
        await deleteResourceTags(selectedIds.value);
        fetchData();
      }
    });
  };

  const handleCreate = () => {
    isCreateTagDialogShow.value = true;
  }

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };
</script>

<style scoped lang="less">
  .title-divider {
    color: #dcdee5;
    margin-right: 16px;
    margin-left: 7px;
  }

  :deep(.table-box) {
    .operation-box() {
      display: flex;
      align-items: center;

      &:hover {
        .operation-icon {
          display: block;
        }
      }

      .operation-icon {
        display: none;
        color: #3a84ff;
        cursor: pointer;
        margin-left: 7.5px;
      }
    }

    .ip-box {
      color: #3a84ff;
      .operation-box();
    }

    .tag-box {
      .operation-box();
    }
  }

  .tags-management-container {
    .header-action {
      display: flex;

      .operation-btn {
        width: 88px;
        margin-right: 8px;
      }

      .search-selector {
        margin-left: auto;
      }
    }
  }

  .batch-delete-wrapper {
    .tags-info {
      display: flex;

      .tags-info-title {
        width: 42px;
      }

      .tags-info-content {
        color: #313238;
      }
    }

    .batch-delete-tip {
      background: #f5f6fa;
      border-radius: 2px;
      padding: 12px 16px;
    }
  }

  .bk-pop-confirm-title {
    font-size: 16px !important;
    color: #313238 !important;
  }
</style>
