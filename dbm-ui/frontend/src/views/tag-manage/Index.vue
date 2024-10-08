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
        <BusinessSelector @change="handleBizChange" />
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
      <DbTable
        ref="tableRef"
        class="table-box"
        :columns="tableColumn"
        :data-source="listTag"
        :disable-select-method="disableSelectMethod"
        remote-sort
        row-class="table-row"
        selectable
        sort-type="ordering"
        @clear-search="clearSearchValue"
        @request-success="handleRequestSuccess"
        @selection="handleSelection" />
    </div>
    <CreateTag
      v-model:is-show="isCreateTagDialogShow"
      :biz="curBiz"
      @create="handleCreateSuccess" />
  </div>
</template>

<script setup lang="tsx">
  import { Button, InfoBox } from 'bkui-vue';
  import BKPopConfirm from 'bkui-vue/lib/pop-confirm';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceTagModel from '@services/model/db-resource/ResourceTag';
  import { deleteTag, getTagRelatedResource, listTag, updateTag } from '@services/source/tag';

  import { useGlobalBizs } from '@stores';

  import BusinessSelector from '@views/tag-manage/components/BusinessSelector.vue';
  import CreateTag from '@views/tag-manage/components/CreateTag.vue'
  import EditableCell from '@views/tag-manage/components/EditableCell.vue';

  import { getSearchSelectorParams, messageSuccess } from '@utils';

  const { t } = useI18n();
  const { bizIdMap, currentBizInfo } = useGlobalBizs();
  const route = useRoute();
  const router = useRouter();

  const tableRef = ref();
  const selected = ref<ResourceTagModel[]>([]);
  const isCreateTagDialogShow = ref(false);
  const curBiz = ref(currentBizInfo!);
  const curEditId = ref(-1);
  const searchValue = ref([]);
  const bindIpMap = ref<Map<number, number>>(new Map()); // 标签ID与当前标签绑定的IP数的映射

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isBusiness = route.name === 'BizResourceTag';

  const { run: runDelete } = useRequest(deleteTag, {
    manual: true,
    onSuccess() {
      fetchData();
      messageSuccess(t('删除成功'));
    }
  });
  const { run: runUpdate } = useRequest(updateTag, {
    manual: true,
    onSuccess() {
      curEditId.value = -1;
      fetchData();
      messageSuccess(t('更新成功'));
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

  const tableColumn = computed(
    () => [
      {
        label: t('标签'),
        field: 'value',
        render: ({ data }: { data: ResourceTagModel }) => (
          bindIpMap.value.get(data.id) ? data.value :
            <EditableCell
              data={data}
              editId={curEditId.value}
              onBlur={handleBlur}
              onEdit={handleEdit}
            />
        )
      },
      {
        label: t('绑定的IP'),
        field: 'count',
        render: ({ data }: { data: ResourceTagModel }) => {
          if (!bindIpMap.value.get(data.id)) {
            return 0;
          }
          const { href } = router.resolve({
            name: isBusiness ? 'BizResourcePool' : 'resourcePool',
            query: {
              label: data.id
            },
            params: {
              page: isBusiness ? 'business' : 'host-list'
            }
          });
          return (
            <a href={href} target='_blank'>
              {bindIpMap.value.get(data.id)}
            </a>)
        },
      },
      {
        label: t('创建人'),
        sort: true,
        field: 'creator',
        render: ({ data }: { data: ResourceTagModel }) => data.creator || '--',
      },
      {
        label: t('创建时间'),
        sort: true,
        field: 'create_at',
        render: ({ data }: { data: ResourceTagModel }) => data.createAtDisplay || '--',
      },
      {
        label: t('操作'),
        render: ({ data }: { data: ResourceTagModel }) => (
          <BKPopConfirm
            width={280}
            trigger='click'
            title={t('确认删除该标签值？')}
            ext-cls='content-wrapper'
            onConfirm={() => handleDelete(data)}
          >
            {{
              default: (
                <Button
                  theme='primary'
                  text
                  disabled={!!bindIpMap.value.get(data.id)}
                  v-bk-tooltips={{
                    content: t('该标签已被绑定 ，不能删除'),
                    disabled: !bindIpMap.value.get(data.id),
                  }}>
                  {t('删除')}
                </Button>
              ),
              content: (
                <>
                  <div>{t('标签：')}<span style="color: '#313238'">{data.value}</span></div>
                  <div class="mb-10 mt-4">{t('删除操作无法撤回，请谨慎操作！')}</div>
                </>
              )
            }}
          </BKPopConfirm>
        )
      }
    ]
  );

  const { run: getRelatedResource } = useRequest(getTagRelatedResource, {
    manual: true,
    onSuccess(data) {
      bindIpMap.value = new Map(data.map((item) => [item.id, item.ip_count]));
    }
  });

  watch(searchValue, () => {
    fetchData();
  });

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData({
      ...searchParams,
      bk_biz_id: curBiz.value.bk_biz_id,
      ordering: '-create_at',
    });
  };

  const handleSelection = (_data: ResourceTagModel, list: ResourceTagModel[]) => {
    selected.value = list;
  };

  const handleBatchDelete = () => {
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
                selected.value.map(v => v.value).join(',')
              }
            </div>
          </div>
          <div class='tips'>{t('删除后将无法恢复，请谨慎操作')}</div>
        </div>
      ),
      onConfirm: () => {
        runDelete({
          bk_biz_id: curBiz.value.bk_biz_id,
          ids: selectedIds.value
        });
      }
    });
  };

  const handleCreate = () => {
    isCreateTagDialogShow.value = true;
  }

  const handleBlur = (data: ResourceTagModel, val: string) => {
    runUpdate({
      bk_biz_id: curBiz.value.bk_biz_id,
      id: data.id,
      value: val,
    });

  }

  const handleEdit = (data: ResourceTagModel) => {
    curEditId.value = data.id;
  }

  const handleDelete = (data: ResourceTagModel) => {
    runDelete({
      bk_biz_id: curBiz.value.bk_biz_id,
      ids: [data.id]
    });
  }

  const handleBizChange = (bkBizId: number) => {
    curBiz.value = bizIdMap.get(bkBizId)!;
    fetchData();
  }

  const disableSelectMethod = (data: ResourceTagModel) => bindIpMap.value.get(data.id) ? t('该标签已被绑定 ，不能删除') : false;

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
      bk_biz_id: curBiz.value.bk_biz_id,
      ids: data.results.map(item => item.id),
      resource_type: 'resource',
    });
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

  :deep(.table-row) {
    .tag-box {
      display: flex;
      align-items: center;

      .tag-content {
        display: flex;
        align-items: center;
      }

      .operation-icon {
        color: #3a84ff;
        cursor: pointer;
        margin-left: 7.5px;
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
