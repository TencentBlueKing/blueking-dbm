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
          :disable-select-method="disableSelectMethod"
          primary-key="tag"
          remote-sort
          selectable
          @clear-search="clearSearchValue"
          @selection="handleSelection" />
      </div>
    </div>
    <CreateTag
      v-model:is-show="isCreateTagDialogShow"
      :biz="curBiz"
      @create="handleCreateSuccess" />
  </div>
</template>

<script setup lang="tsx">
  import { Button, InfoBox, Message } from 'bkui-vue';
  import BKPopConfirm from 'bkui-vue/lib/pop-confirm';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteTag, getTagRelatedResource, listTag, updateTag } from '@services/source/tag';

  import { useGlobalBizs } from '@stores';

  import BusinessSelector from '@views/tag-manage/components/BusinessSelector.vue';
  import CreateTag from '@views/tag-manage/components/CreateTag.vue'
  import EditableCell from '@views/tag-manage/components/EditableCell.vue';

  import ResourceTag from '@/services/model/db-resource/ResourceTag';
  import { getSearchSelectorParams } from '@/utils';

  type ResourceTagModel = ServiceReturnType<typeof listTag>['results'][number];

  const { t } = useI18n();
  const { bizIdMap, currentBizInfo } = useGlobalBizs();
  const route = useRoute();

  const tableRef = ref();
  const selected = ref<ResourceTagModel[]>([]);
  const isCreateTagDialogShow = ref(false);
  const curBiz = ref(currentBizInfo);
  const curEditId = ref(-1);
  const searchValue = ref([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isBusiness = computed(() => route.name === 'BizResourceTag');

  const { run: runDelete } = useRequest(deleteTag, {
    manual: true,
    onSuccess() {
      fetchData();
      Message({
        message: t('删除成功'),
        theme: 'success',
      });
    }
  });
  const { run: runUpdate } = useRequest(updateTag, {
    manual: true,
    onAfter() {
      curEditId.value = -1;
      fetchData();
      Message({
        message: t('更新成功'),
        theme: 'success',
      });
    }
  });

  const searchSelectData = [
    {
      name: t('标签'),
      id: 'value',
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
      render: ({ data }: { data: ResourceTagModel }) => (
        data.isBinded ? data.tag :
          <EditableCell
            data={data}
            isEdit={data.id === curEditId.value}
            onBlur={handleBlur}
            onEdit={handleEdit}
          />
      )
    },
    {
      label: t('绑定的IP'),
      field: 'count',
    },
    {
      label: t('创建人'),
      sort: true,
      field: 'creator',
    },
    {
      label: t('创建时间'),
      sort: true,
      field: 'creationTime',
      render: ({ data }: { data: ResourceTagModel }) => data.creationTimeDisplay,
    },
    {
      label: t('操作'),
      render: ({ data }: { data: ResourceTagModel }) => (
        <BKPopConfirm
          width={280}
          trigger='click'
          title={t('确认删除该标签值？')}
          ext-cls={'content-wrapper'}
          onConfirm={() => handleDelete(data)}
        >
          {{
            default: <Button theme='primary' text disabled={data.isBinded} v-bk-tooltips={{
              content: t('该标签已被绑定 ，不能删除'),
              disabled: !data.isBinded,
            }}>删除</Button>,
            content: (
              <div>
                <div>{t('标签：')}<span style="color: '#313238'">{data.tag}</span></div>
                <div class="mb-10 mt-4">{t('删除操作无法撤回，请谨慎操作！')}</div>
              </div>
            )
          }}
        </BKPopConfirm>
      )
    }
  ];

  watch(searchValue, () => {
    fetchData();
  });

  const fetchData = async () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    await tableRef.value.fetchData(searchParams);
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
        <div class='tag-manage-batch-delete-wrapper'>
          <div class='tag-wrapper'>
            <div class='tag'>
              {t('标签:')}
            </div>
            <div class='content'>
              {
                selected.value.map(v => v.tag).join(',')
              }
            </div>
          </div>
          <div class='tips'>
            {
              t('删除后将无法恢复，请谨慎操作')
            }
          </div>
        </div>
      ),
      onConfirm: async () => {
        runDelete({
          bk_biz_id: curBiz.value?.bk_biz_id as number,
          ids: selectedIds.value
        });
      }
    });
  };

  const handleCreate = () => {
    isCreateTagDialogShow.value = true;
  }

  const handleBlur = async (data: ResourceTagModel, val: string) => {
    runUpdate({
      bk_biz_id: curBiz.value?.bk_biz_id as number,
      id: data.id,
      value: val,
    });

  }

  const handleEdit = (data: ResourceTagModel) => {
    curEditId.value = data.id;
  }

  const handleDelete = async (data: ResourceTagModel) => {
    await runDelete({
      bk_biz_id: curBiz.value?.bk_biz_id as number,
      ids: [data.id]
    });
    fetchData();
  }

  const handleBizChange = (bkBizId: number) => {
    curBiz.value = bizIdMap.get(bkBizId);
    fetchData();
  }

  const disableSelectMethod = (data: ResourceTagModel) => data.isBinded ? t('该标签已被绑定 ，不能删除') : false;

  const clearSearchValue = () => {
    searchValue.value = [];
    tableRef.value?.fetchData();
  };

  const handleCreateSuccess = async () => {
    await fetchData();
    Message({
      theme: 'success',
      message: t('创建成功'),
    })
  };

  const getDataSource = async (params: ServiceParameters<typeof listTag>) => {
    const res = await listTag(params);
    const ids = res.results.map(item => item.id);
    const resourceData = await getTagRelatedResource({
      bk_biz_id: curBiz.value?.bk_biz_id as number,
      ids,
    });
    const map = new Map<number, number>();
    resourceData.forEach(item => {
      const dbResource = item.related_resources.find(resource => resource.resource_type === 'db_resource');
      if (dbResource) {
        map.set(item.id, dbResource.count);
      }
    });
    return {
      ...res,
      results: res.results.map((item: ResourceTag) => new ResourceTag({
        ...item,
        count: map.get(item.id),
      })),
    }
  };

  onMounted(() => {
    fetchData();
  });
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
      .operation-box();

      .ip-count {
        color: #3a84ff;
        cursor: pointer;
      }
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
        width: 560px;
        height: 32px;
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
      align-items: top;
      font-size: 14px;

      .tag {
        text-align: left;
      }

      .content {
        flex: 1;
        color: #313238;
        text-align: left;
        margin-left: 14px;
        word-break: break-all;
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

  .content-wrapper {
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
