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
      <div
        v-if="!isBusiness"
        class="tag-manage-header-container">
        <BkTag
          class="ml-8"
          theme="info">
          {{ t('全局') }}
        </BkTag>
        <span class="title-divider">|</span>
        <DbAppSelect
          :list="bizs"
          :model-value="curBiz"
          type="text"
          @change="handleBizChange">
        </DbAppSelect>
      </div>
      <div
        v-else
        class="tag-manage-header-container">
        <BkTag
          class="ml-8"
          theme="info">
          {{ t('业务') }}
        </BkTag>
      </div>
    </Teleport>
    <div class="tags-management-container">
      <div class="header-action mb-16">
        <BkButton
          class="operation-btn"
          :disabled="curBiz?.bk_biz_id === 0"
          theme="primary"
          @click="handleCreate">
          {{ t('新建') }}
        </BkButton>
        <BkButton
          class="operation-btn"
          :disabled="!hasSelected"
          @click="handleBatchDelete">
          {{ t('批量删除') }}
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
      <DbTable
        ref="tableRef"
        class="table-box"
        :data-source="listTag"
        :disable-select-method="disableSelectMethod"
        row-class-name="table-row"
        row-key="id"
        selectable
        @clear-search="clearSearchValue"
        @request-success="handleRequestSuccess"
        @selection="handleSelection">
        <TableColumn
          col-key="id"
          title="ID"
          :width="80">
          <template #default="{ row: data }: { row: ResourceTagModel }">
            {{ data.id || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="value"
          :min-width="200"
          :title="t('标签')">
          <template #default="{ row: data }: { row: ResourceTagModel }">
            <span v-if="bindIpMap.get(data.id)">{{ data.value }}</span>
            <EditableCell
              v-else
              :data="data"
              :edit-id="curEditId"
              @blur="handleBlur"
              @edit="handleEdit" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="count"
          :title="t('绑定的IP')"
          :width="120">
          <template #default="{ row: data }: { row: ResourceTagModel }">
            <a
              v-if="bindIpMap.get(data.id)"
              :href="getResourcePoolUrl(data)"
              target="_blank">
              {{ bindIpMap.get(data.id) }}
            </a>
            <span v-else>0</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="creator"
          sorter
          :title="t('创建人')"
          :width="160">
          <template #default="{ row: data }: { row: ResourceTagModel }">
            {{ data.creator || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="create_at"
          sorter
          :title="t('创建时间')"
          :width="180">
          <template #default="{ row: data }: { row: ResourceTagModel }">
            {{ data.createAtDisplay || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="operation"
          :title="t('操作')"
          :width="120">
          <template #default="{ row: data }: { row: ResourceTagModel }">
            <BkPopConfirm
              ext-cls="tag-delelte-popconfirm-content-wrapper"
              :title="t('确认删除该标签值？')"
              trigger="click"
              :width="280"
              @confirm="handleDelete(data)">
              <template #content>
                <div>
                  {{ t('标签：') }}
                  <span style="color: #313238">{{ data.value }}</span>
                </div>
                <div class="mb-10 mt-4">{{ t('删除操作无法撤回，请谨慎操作！') }}</div>
              </template>
              <BkButton
                v-bk-tooltips="{
                  content: t('该标签已被绑定 ，不能删除'),
                  disabled: !bindIpMap.get(data.id),
                }"
                :disabled="!!bindIpMap.get(data.id)"
                text
                theme="primary">
                {{ t('删除') }}
              </BkButton>
            </BkPopConfirm>
          </template>
        </TableColumn>
      </DbTable>
    </div>
    <CreateTag
      v-model:is-show="isCreateTagDialogShow"
      :biz-id="curBiz?.bk_biz_id"
      @create="handleCreateSuccess" />
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceTagModel from '@services/model/db-resource/ResourceTag';
  import type { getBizs } from '@services/source/cmdb';
  import { deleteTag, getTagRelatedResource, listTag, updateTag, validateTag } from '@services/source/tag';

  import { useGlobalBizs } from '@stores';

  import DbAppSelect from '@components/db-app-select/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { getSearchSelectorParams, messageSuccess } from '@utils';

  import CreateTag from './components/CreateTag.vue';
  import EditableCell from './components/EditableCell.vue';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { bizs, currentBizInfo, publicBiz } = useGlobalBizs();

  const isBusiness = route.name === 'BizResourceTag';

  const tableRef = ref();
  const selected = ref<ResourceTagModel[]>([]);
  const isCreateTagDialogShow = ref(false);

  const curEditId = ref(-1);
  const searchValue = ref([]);

  const curBiz = shallowRef(isBusiness ? currentBizInfo : publicBiz);
  const bindIpMap = shallowRef<Map<number, number>>(new Map()); // 标签ID与当前标签绑定的IP数的映射

  const searchSelectData = [
    {
      id: 'value',
      name: t('标签'),
    },
    {
      id: 'creator',
      name: t('创建人'),
    },
  ];

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const { run: runDelete } = useRequest(deleteTag, {
    manual: true,
    onSuccess() {
      fetchData();
      messageSuccess(t('删除成功'));
    },
  });

  const { run: getRelatedResource } = useRequest(getTagRelatedResource, {
    manual: true,
    onSuccess(data) {
      bindIpMap.value = new Map(data.map((item) => [item.id, item.ip_count]));
    },
  });

  const { run: runUpdate } = useRequest(updateTag, {
    manual: true,
    onSuccess() {
      curEditId.value = -1;
      fetchData();
      messageSuccess(t('更新成功'));
    },
  });

  watch(searchValue, () => {
    fetchData();
  });

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData({
      ...searchParams,
      bk_biz_id: curBiz.value?.bk_biz_id,
      ordering: '-create_at',
      type: 'resource',
    });
  };

  const getResourcePoolUrl = (data: ResourceTagModel) => {
    const { href } = router.resolve({
      name: isBusiness ? 'BizResourcePool' : 'resourcePool',
      params: {
        page: isBusiness ? 'business' : 'host-list',
      },
      query: {
        label_names: data.value,
      },
    });
    return href;
  };

  const handleSelection = (_idList: string[], list: ResourceTagModel[]) => {
    selected.value = list;
  };

  const handleBatchDelete = () => {
    InfoBox({
      cancelText: t('取消'),
      class: 'batch-delete-wrapper',
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      content: (
        <div class='tag-manage-batch-delete-wrapper'>
          <div class='tag-wrapper'>
            <div class='tag'>{t('标签:')}</div>
            <div class='content'>{selected.value.map((v) => v.value).join(',')}</div>
          </div>
          <div class='tips'>{t('删除后将无法恢复，请谨慎操作')}</div>
        </div>
      ),
      onConfirm: () => {
        runDelete({
          bk_biz_id: curBiz.value!.bk_biz_id,
          ids: selectedIds.value,
        });
      },
      title: t('确认批量删除n个标签？', { n: selected.value.length }),
      width: 480,
    });
  };

  const handleCreate = () => {
    isCreateTagDialogShow.value = true;
  };

  const handleBlur = (data: ResourceTagModel, val: string) => {
    if (val && data.value !== val) {
      validateTag({
        bk_biz_id: curBiz.value!.bk_biz_id,
        tags: [{ key: 'dbresource', value: val }],
        type: 'resource',
      }).then((existData) => {
        if (existData.length === 0) {
          runUpdate({
            bk_biz_id: curBiz.value!.bk_biz_id,
            id: data.id,
            type: 'resource',
            value: val,
          });
        } else {
          curEditId.value = -1;
        }
      });
    } else {
      curEditId.value = -1;
    }
  };

  const handleEdit = (data: ResourceTagModel) => {
    curEditId.value = data.id;
  };

  const handleDelete = (data: ResourceTagModel) => {
    runDelete({
      bk_biz_id: curBiz.value!.bk_biz_id,
      ids: [data.id],
    });
  };

  const handleBizChange = (appInfo?: IAppItem) => {
    curBiz.value = appInfo;
    fetchData();
  };

  const disableSelectMethod = (data: ResourceTagModel) =>
    bindIpMap.value.get(data.id) ? t('该标签已被绑定 ，不能删除') : false;

  const clearSearchValue = () => {
    searchValue.value = [];
    tableRef.value?.fetchData();
  };

  const handleCreateSuccess = () => {
    fetchData();
    messageSuccess(t('创建成功'));
  };

  const handleRequestSuccess = (data: ServiceReturnType<typeof listTag>) => {
    getRelatedResource({
      bk_biz_id: curBiz.value!.bk_biz_id,
      ids: data.results.map((item) => item.id),
      resource_type: 'resource',
    });
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less" scoped>
  .title-divider {
    margin-right: 16px;
    margin-left: 7px;
    color: #dcdee5;
  }

  :deep(.table-row) {
    .tag-box {
      display: flex;
      align-items: center;

      .tag-content {
        display: flex;
        align-items: center;
      }

      .operation-icon {
        margin-left: 7.5px;
        color: #3a84ff;
        cursor: pointer;
        visibility: hidden;
      }
    }

    &:hover .tag-box .operation-icon {
      visibility: visible;
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
        width: 560px;
        height: 32px;
        margin-left: auto;
      }
    }
  }
</style>

<style lang="less">
  .tag-manage-header-container {
    display: flex;
    align-items: center;
  }

  .tag-manage-batch-delete-wrapper {
    .tag-wrapper {
      display: flex;
      align-items: flex-start;
      font-size: 14px;

      .tag {
        text-align: left;
      }

      .content {
        margin-left: 14px;
        color: #313238;
        text-align: left;
        word-break: break-all;
        flex: 1;
      }
    }

    .tips {
      padding: 12px 16px;
      margin-top: 16px;
      font-size: 14px;
      text-align: left;
      background: #f5f6fa;
      border-radius: 2px;
    }
  }

  .tag-delelte-popconfirm-content-wrapper {
    .bk-pop-confirm-title {
      font-size: 16px !important;
      color: #313238 !important;
    }

    .bk-button.bk-button-primary {
      background-color: #ea3636;
      border-color: #ea3636;
    }
  }
</style>
