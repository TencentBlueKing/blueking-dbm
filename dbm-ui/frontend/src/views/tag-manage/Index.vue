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
      <section
        v-if="!isBusiness"
        class="tag-manage-header-container">
        <BkTag
          class="ml-8"
          theme="info">
          {{ t('全局') }}
        </BkTag>
        <span class="title-divider">|</span>
        <BusinessSelector @change="handleBizChange" />
      </section>
      <section
        v-else
        class="tag-manage-header-container">
        <BkTag
          class="ml-8"
          theme="info">
          {{ t('业务') }}
        </BkTag>
      </section>
    </Teleport>
    <div class="tags-management-container">
      <div class="header-action mb-16">
        <BkButton
          class="operation-btn"
          theme="primary"
          @click="handleCreate"
          >{{ t('新建') }}
        </BkButton>
        <BkButton
          class="operation-btn"
          :disabled="!hasSelected"
          @click="handleBatchDelete"
          >{{ t('批量删除') }}
        </BkButton>
        <BkSearchSelect
          v-model="searchValue"
          class="search-selector"
          :data="searchSelectData"
          :placeholder="t('请输入标签关键字')"
          unique-select
          value-split-code="+"
          @search="fetchData" />
      </div>
      <div>
        <DbTable
          ref="tableRef"
          class="table-box"
          :columns="tableColumn"
          :data-source="getDataSource"
          primary-key="tag"
          selectable
          @clear-search="clearSearchValue"
          @selection="handleSelection" />
      </div>
    </div>
    <CreateTag
      v-model:is-show="isCreateTagDialogShow"
      :biz="curBiz as BizItem" />
  </div>
</template>

<script setup lang="tsx">
  import { Button, InfoBox } from 'bkui-vue';
  import BKPopConfirm from 'bkui-vue/lib/pop-confirm';
  import { useI18n } from 'vue-i18n';

  import { deleteResourceTags, getResourceTags, modifyResourceTag } from '@services/source/resourceTag';
  import type { BizItem } from '@services/types';

  import { useCopy, useLinkQueryColumnSerach } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const/clusterTypes';

  import BusinessSelector from '@views/tag-manage/BusinessSelector.vue';
  import CreateTag from '@views/tag-manage/CreateTag.vue'

  import EditableCell from './EditableCell.vue';

  type ResourceTagModel = ServiceReturnType<typeof getResourceTags>['results'][number];

  export type ResourceTagListItem = ResourceTagModel & { is_show_edit: boolean };

  const { t } = useI18n();
  const copy = useCopy();
  const { bizIdMap, currentBizInfo } = useGlobalBizs();
  const route = useRoute();
  const {
    searchValue,
    clearSearchValue,
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
  const selected = ref<ResourceTagListItem[]>([]);
  const isCreateTagDialogShow = ref(false);
  const curBiz = ref(currentBizInfo);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isBusiness = computed(() => route.path.includes('business-resource-tag'));
  const searchSelectData = [
    {
      name: t('标签'),
      id: 'tag',
    },
    {
      name: t('IP'),
      id: 'boundIp',
    },
    {
      name: t('创建人'),
      id: 'creator',
    }
  ];

  const tableColumn = [
    {
      label: t('标签'),
      field: 'tag',
      render: ({ data }: { data: ResourceTagListItem }) => (
        <EditableCell
          data={data}
          onBlur={handleBlur}
          onEdit={handleEdit}
        />
      )
    },
    {
      label: t('绑定的IP'),
      field: 'boundIp',
      render: ({ data }: { data: ResourceTagListItem }) => (
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
            onClick={() => handleCopy(data)} />
        </div>
      )
    },
    {
      label: t('创建人'),
      field: 'creator',
    },
    {
      label: t('创建时间'),
      field: 'creationTime',
      render: ({ data }: { data: ResourceTagListItem }) => data.creationTimeDisplay,
    },
    {
      label: t('操作'),
      render: ({ data }: { data: ResourceTagListItem }) => (
        <BKPopConfirm
          width={280}
          trigger='click'
          title={t('确认删除该标签值？')}
          onConfirm={() => handleDelete(data)}
        >
          {{
            default: <Button theme='primary' text>删除</Button>,
            content: (
              <div>
                <div>{t('标签：')}<span style="color: '#313238'">{data.tag}</span></div>
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

  const getDataSource = async () => {
    const res = await getResourceTags();
    const tmp = {
      ...res,
      results: res.results.map((item: ResourceTagModel) => (
        Object.defineProperty(item, 'is_show_edit', {
          value: false,
          writable: true,
          configurable: true,
          enumerable: true,
        })
      )),
    };
    return tmp;
  }

  const handleSelection = (_data: ResourceTagListItem, list: ResourceTagListItem[]) => {
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
        <div class='tag-manage-batch-delete-wrapper'>
          <div class='tag-wrapper'>
            <div class='tag'>
              {t('标签:')}
            </div>
            <div class='content'>
              {
                selected.value.map(v => v.tag).join(',')
              }
            </div>∏∏
          </div>
          <div class='tips'>
            {
              t('删除后将无法恢复，请谨慎操作')
            }
          </div>
        </div>
      ),
      onConfirm: async () => {
        await deleteResourceTags({ ids: selectedIds.value });
        fetchData();
      }
    });
  };

  const handleCreate = () => {
    isCreateTagDialogShow.value = true;
  }

  const handleBlur = async (data: ResourceTagListItem) => {
    try {
      await modifyResourceTag({ data });
    }
    finally {
      Object.assign(data, {
        is_show_edit: false,
      });
    }
  }

  const handleEdit = (data: ResourceTagListItem) => {
    Object.assign(data, {
      is_show_edit: true,
    });
  }

  const handleDelete = async (data: ResourceTagListItem) => {
    await deleteResourceTags({
      ids: [data.id]
    });
    fetchData();
  }

  const handleCopy = (data: ResourceTagListItem) => {
    copy(data.boundIp.join('\n'));
  }

  const handleBizChange = (bkBizId: number) => {
    curBiz.value = bizIdMap.get(bkBizId);
    fetchData();
  }
</script>

<style lang="less" scoped>
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
        width: 400px;
      }
    }
  }

  .bk-pop-confirm-title {
    font-size: 16px !important;
    color: #313238 !important;
  }
</style>

<style lang="less">
  .tag-manage-header-container {
    display: flex;
    align-items: center;

    .business-selector {
      cursor: pointer;
      color: #3a84ff;
      display: flex;
      align-items: center;
      font-size: 14px;
      width: 360px;

      .triangle {
        width: 0;
        height: 0;
        border-left: 4.875px solid transparent;
        border-right: 4.875px solid transparent;
        border-top: 6px solid #3a84ff;
        transition: transform 0.3s ease;
        margin-left: 7px;

        &.up {
          transform: rotate(180deg);
        }
      }
    }
  }

  .tag-manage-batch-delete-wrapper {
    .tag-wrapper {
      display: flex;
      font-size: 14px;

      .tag {
        text-align: left;
      }

      .content {
        flex: 1;
        color: #313238;
      }
    }

    .tips {
      background: #f5f6fa;
      border-radius: 2px;
      padding: 12px 16px;
      margin-top: 16px;
      text-align: left;
      font-size: 14px;
    }
  }
</style>
