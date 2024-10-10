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
          :data-source="getResourceTags"
          primary-key="tag"
          selectable
          @clear-search="clearSearchValue"
          @selection="handleSelection" />
      </div>
    </div>
    <CreateTag
      v-model:is-show="isCreateTagDialogShow"
      bk-biz-id="1" />
  </div>
</template>

<script setup lang="tsx">
  import { Button, InfoBox } from 'bkui-vue';
  import BKPopConfirm from 'bkui-vue/lib/pop-confirm';
  import { useI18n } from 'vue-i18n';

  import type ResourceTagModel from '@services/model/db-resource/ResourceTag';
  import { deleteResourceTags, getResourceTags, modifyResourceTag } from '@services/source/tag';

  import { ClusterTypes } from '@common/const/clusterTypes';

  import AutoFocusInput from '@views/tag-manage/AutoFocusInput.vue'
  import CreateTag from '@views/tag-manage/CreateTag.vue'

  import { useCopy } from '@/hooks';
  import { useLinkQueryColumnSerach } from '@/hooks/useLinkQueryColumnSerach';

  const { t } = useI18n();
  const copy = useCopy();
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
  const selected = ref<ResourceTagModel[]>([]);
  const isCreateTagDialogShow = ref(false);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const searchSelectData = [
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
  ];

  const tableColumn = [
    {
      label: '标签',
      field: 'tag',
      render: ({ data }: { data: ResourceTagModel }) => {
        const renderTag = () => {
          if (data.is_show_edit) {
            return (
              <AutoFocusInput modelValue={data.tag} clearable={false} onBlur={() => handleBlur(data)} />
            )
          }
          return (
            <>
              <span>{data.tag}</span>
              <db-icon
                class="operation-icon"
                type="edit"
                style="font-size: 18px"
                onClick={() => handleEdit(data)} />
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
          onConfirm={() => handleDelete(data)}
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

  const handleBlur = async (data: ResourceTagModel) => {
    try {
      await modifyResourceTag(data);
    }
    finally {
      Object.assign(data, {
        is_show_edit: false,
      });
    }
  }

  const handleEdit = (data: ResourceTagModel) => {
    Object.assign(data, {
      is_show_edit: true,
    });
  }

  const handleDelete = async (data: ResourceTagModel) => {
    await deleteResourceTags([data.id]);
    fetchData();
  }
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
        width: 400px;
      }
    }
  }

  .bk-pop-confirm-title {
    font-size: 16px !important;
    color: #313238 !important;
  }
</style>

<style lang="less"></style>
