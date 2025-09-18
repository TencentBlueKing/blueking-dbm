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
  <div class="cluster-tag-manage-page">
    <div class="header-action mb-16">
      <AuthButton
        action-id="resource_tag_manage"
        :biz-id="bizId"
        class="operation-btn"
        theme="primary"
        @click="handleCreate">
        {{ t('新建') }}
      </AuthButton>
      <AuthButton
        action-id="resource_tag_manage"
        :biz-id="bizId"
        class="operation-btn"
        :disabled="!hasSelected"
        @click="handleBatchDelete">
        {{ t('批量删除') }}
      </AuthButton>
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
      :data-source="listClusterTag"
      :merge-cells="mergeCells"
      @request-finished="handleRequestFinished">
      <BkTableColumn
        field="key"
        :label="t('标签键')"
        :min-width="350">
        <template #default="{ data, rowIndex }: { data: RowData, rowIndex: number }">
          <div
            class="tag-key-column-main"
            @click="() => handleToggleRowExpand(rowIndex, data.key)">
            <TextOverflowLayout>
              <template #prepend>
                <BkCheckbox
                  v-bk-tooltips="{
                    disabled: !isKeyApplied(data.key),
                    content: t('已被应用，无法删除'),
                  }"
                  class="mr-8"
                  :disabled="isKeyApplied(data.key)"
                  :model-value="selectedMap[data.key]"
                  @change="(checked: boolean) => handleChooseKey(checked, data.key)" />
                <DbIcon
                  v-if="rowMergeCountMap[data.key]?.count > 1"
                  class="toggle-icon"
                  :class="{ 'is-open': toggleInfoMap[data.key] }"
                  type="down-shape" />
              </template>
              <span :style="{ paddingLeft: rowMergeCountMap[data.key]?.count > 1 ? '0px' : '20px' }">{{
                data.key
              }}</span>
              <template #append>
                <BkPopConfirm
                  ext-cls="append-tag-pop-confirm-main"
                  :title="t('追加标签')"
                  trigger="click"
                  :width="430"
                  @after-hidden="handlecancelAppendTagValue"
                  @confirm="handleConfirmAppendTagValue">
                  <template #content>
                    <div class="append-tag-main">
                      <div class="title-main">{{ t('标签值') }}</div>
                      <TagValueInput
                        v-model="appendTagValues"
                        class="mt-6" />
                    </div>
                  </template>
                  <BkButton
                    class="append-btn"
                    :class="{ 'is-always-show': appendTagVisableMap[data.id] }"
                    size="small"
                    @click.stop="() => handleClickAppend(data.key, data.id)">
                    {{ t('追加标签值') }}
                  </BkButton>
                </BkPopConfirm>
              </template>
            </TextOverflowLayout>
          </div>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="value"
        :label="t('标签值')"
        :min-width="450"
        show-overflow="tooltip">
        <template #default="{ data, rowIndex }: { data: RowData, rowIndex: number }">
          <RenderTagOverflow
            v-if="isCollapsed(data.key)"
            :data="generateRowsTags(data.key)" />
          <EditableCell
            v-else
            :data="data.value"
            :show-edit="!data.clusters.length"
            @success="(value: string) => handleEditSingleValueSuccess(rowIndex, value)" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="clusters"
        :label="t('绑定的集群')"
        :min-width="300"
        show-overflow="tooltip">
        <template #default="{ data }: { data: RowData }">
          <div class="bind-cluster-column-main">
            <BkButton
              v-if="calcTagClusters(data)"
              v-bk-tooltips="tagClustersToolTip(data)"
              text
              theme="primary">
              {{ calcTagClusters(data) }}
            </BkButton>
            <span v-else>0</span>
            <DbIcon
              v-if="calcTagClusters(data)"
              v-bk-tooltips="tagClustersToolTip(data)"
              class="copy-icon"
              type="copy"
              @click="() => execCopy(tagClustersToolTip(data))" />
          </div>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="creator"
        :label="t('创建人')"
        show-overflow="tooltip"
        :width="160">
      </BkTableColumn>
      <BkTableColumn
        field="createAtDisplay"
        :label="t('创建时间')"
        :min-width="200">
      </BkTableColumn>
      <BkTableColumn
        fixed="right"
        :label="t('操作')"
        :min-width="120">
        <template #default="{ data, rowIndex }: { data: RowData, rowIndex: number }">
          <AuthButton
            v-if="calcTagClusters(data)"
            v-bk-tooltips="{
              disabled: !data.permission.resource_tag_manage || !calcKeyRelatedClusters(data.key).length,
              content: t('绑定的集群不为 0 ，不能删除'),
            }"
            action-id="resource_tag_manage"
            disabled
            :permission="data.permission.resource_tag_manage"
            text
            theme="primary">
            {{ t('删除') }}
          </AuthButton>
          <BkPopConfirm
            v-else
            :confirm-config="{
              theme: 'danger',
            }"
            ext-cls="delete-tag-pop-confirm-main"
            :title="
              rowMergeCountMap[data.key]?.count === 1
                ? t('确定删除该标签？')
                : isCollapsed(data.key)
                  ? t('确认删除该标签键下所有标签？')
                  : t('确认删除该标签值？')
            "
            trigger="click"
            :width="280"
            @confirm="handleConfirmDeleteTag">
            <template #content>
              <div class="delete-tag-main">
                <div class="content-main">
                  <div class="key-main">
                    <span>{{
                      rowMergeCountMap[data.key]?.count === 1
                        ? t('标签')
                        : isTagKey(data.key)
                          ? t('标签键')
                          : t('标签值')
                    }}</span>
                    <span class="ml-4 mr-4">:</span>
                  </div>
                  <div class="value-main">
                    <span v-if="isCollapsed(data.key)">{{ data.key }}</span>
                    <BkTag v-else>{{ `${data.key} : ${data.value}` }}</BkTag>
                  </div>
                </div>
                <div>{{ t('删除操作无法撤回，请谨慎操作！') }}</div>
              </div>
            </template>
            <AuthButton
              action-id="resource_tag_manage"
              :permission="data.permission.resource_tag_manage"
              text
              theme="primary"
              @click="() => handleDeleteTag(data.key, rowIndex)">
              {{ t('删除') }}
            </AuthButton>
          </BkPopConfirm>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
  <BkDialog
    class="create-tag-dialog-main"
    :is-show="isCreateTagDialogShow"
    :quick-close="false"
    render-directive="if"
    :title="t('新建标签')"
    :width="660"
    @closed="handleClose">
    <CreateTag
      ref="createTagRef"
      :existed-keys="existedKeyList" />
    <template #footer>
      <div class="footer-wrapper">
        <BkButton
          class="mr-8"
          :loading="confirmLoading"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { batchCreateTags, deleteTag, listClusterTag, updateTag } from '@services/source/tag';

  import { tagValueRegex } from '@common/regex';

  import RenderTagOverflow from '@components/render-tag-overflow/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams, messageError, messageSuccess } from '@utils';

  import TagValueInput from './components/add-tag/components/key-value-mode/components/key-value-pair/components/TagValueInput.vue';
  import CreateTag from './components/add-tag/Index.vue';
  import EditableCell from './components/EditableCell.vue';

  type RowData = ServiceReturnType<typeof listClusterTag>['results'][number];

  const { t } = useI18n();

  const createTagRef = ref<InstanceType<typeof CreateTag>>();
  const tableRef = ref();
  const isCreateTagDialogShow = ref(false);
  const searchValue = ref([]);
  const selectedMap = ref<Record<string, boolean>>({});
  const appendTagValues = ref<string[]>([]);
  const toggleInfoMap = ref<Record<string, boolean>>({});
  const existedKeyList = ref<Set<string>>(new Set());
  const appendTagVisableMap = ref<Record<number, boolean>>({});

  const mergeCells = ref<
    {
      col: number;
      colspan: number;
      row: number;
      rowspan: number;
    }[]
  >([]);
  const rowMergeCountMap = ref<
    Record<
      string,
      {
        count: number;
        index: number;
      }
    >
  >({});

  const searchSelectData = [
    {
      id: 'key',
      name: t('标签键'),
    },
    {
      id: 'value',
      name: t('标签值'),
    },
  ];
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  let tableData: RowData[] = [];
  let currentKey = '';
  let currentRowIndex = 0;

  const hasSelected = computed(() => Object.keys(selectedMap.value).length > 0);

  const { run: runDelete } = useRequest(deleteTag, {
    manual: true,
    onSuccess() {
      fetchData();
      messageSuccess(t('删除成功'));
    },
  });

  const { run: runUpdate } = useRequest(updateTag, {
    manual: true,
    onSuccess() {
      fetchData();
      messageSuccess(t('更新成功'));
    },
  });

  const { loading: confirmLoading, run: runBatchCreate } = useRequest(batchCreateTags, {
    manual: true,
    onSuccess() {
      handleClose();
      fetchData();
      messageSuccess(t('新建标签成功'));
    },
  });

  watch(searchValue, () => {
    fetchData();
  });

  const isKeyApplied = (key: string) => {
    const sameKeyList = tableData.filter((item) => item.key === key);
    return !!sameKeyList.find((item) => item.clusters.length > 0);
  };

  const tagClustersToolTip = (data: RowData) =>
    isCollapsed(data.key)
      ? calcKeyRelatedClusters(data.key).join('\n')
      : data.clusters.map((item) => item.domain).join('\n');

  const isCollapsed = (key: string) => !toggleInfoMap.value[key] && rowMergeCountMap.value[key]?.count > 1;

  const isTagKey = (key: string) => isCollapsed(key) || rowMergeCountMap.value[key]?.count === 1;

  const calcKeyRelatedClusters = (key: string) => {
    const sameKeyList = tableData.filter((item) => item.key === key);
    return sameKeyList.reduce<string[]>((results, item) => {
      results.push(...item.clusters.map((cluster) => cluster.domain));
      return results;
    }, []);
  };

  const calcTagClusters = (data: RowData) =>
    isCollapsed(data.key) ? calcKeyRelatedClusters(data.key).length : data.clusters.length;

  const generateRowsTags = (key: string) =>
    tableData.reduce<string[]>((results, item) => {
      if (item.key === key) {
        results.push(item.value);
      }
      return results;
    }, []);

  const handleChooseKey = (checked: boolean, key: string) => {
    if (checked) {
      selectedMap.value[key] = checked;
      return;
    }

    delete selectedMap.value[key];
  };

  const handleEditSingleValueSuccess = (rowIndex: number, value: string) => {
    const currentRowData = tableData[rowIndex];
    tableData[rowIndex].value = value;
    runUpdate({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      id: currentRowData.id,
      type: 'cluster',
      value,
    });
  };

  const handleClickAppend = (key: string, id: number) => {
    currentKey = key;
    appendTagVisableMap.value = {
      [id]: true,
    };
  };

  const handleConfirmAppendTagValue = () => {
    if (!appendTagValues.value.length) {
      return;
    }

    if (appendTagValues.value.some((item) => !tagValueRegex.test(item))) {
      messageError(t('标签值为1-100个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)'));
      return;
    }

    runBatchCreate({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      tags: appendTagValues.value.map((value) => ({
        key: currentKey,
        value,
      })),
      type: 'cluster',
    });
    appendTagValues.value = [];
  };

  const handlecancelAppendTagValue = () => {
    appendTagValues.value = [];
    appendTagVisableMap.value = {};
  };

  const handleDeleteTag = (key: string, index: number) => {
    currentKey = key;
    currentRowIndex = index;
  };

  const handleConfirmDeleteTag = () => {
    let ids: number[] = [];
    if (!toggleInfoMap.value[currentKey] && rowMergeCountMap.value[currentKey].count >= 1) {
      ids = tableData.reduce<number[]>((results, item) => {
        if (item.key === currentKey) {
          results.push(item.id);
        }
        return results;
      }, []);
    } else {
      ids = [tableData[currentRowIndex].id];
    }
    runDelete({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      ids,
    });
  };

  const handleRequestFinished = (dataList: RowData[]) => {
    tableData = dataList;
    existedKeyList.value = dataList.reduce<Set<string>>((results, item) => {
      results.add(item.key);
      return results;
    }, new Set());

    const keysMergeMap: typeof rowMergeCountMap.value = {};
    dataList.forEach((item, index) => {
      if (keysMergeMap[item.key]) {
        keysMergeMap[item.key].count += 1;
      } else {
        toggleInfoMap.value[item.key] = false;
        keysMergeMap[item.key] = {
          count: 1,
          index,
        };
      }
    });
    rowMergeCountMap.value = keysMergeMap;
    const countList = Object.values(keysMergeMap).sort((a, b) => b.count - a.count);
    mergeCells.value = countList.reduce<{ col: number; colspan: number; row: number; rowspan: number }[]>(
      (results, item) => {
        results.push(
          ...Array(6)
            .fill('')
            .map((_, index) => ({
              col: index,
              colspan: 1,
              row: item.index,
              rowspan: item.count,
            })),
        );
        return results;
      },
      [],
    );
  };

  const handleToggleRowExpand = (rowIndex: number, key: string) => {
    const merges = mergeCells.value.filter((item) => item.row === rowIndex);
    const rowSpan = merges[0].rowspan;
    tableRef.value.bkTableRef.getVxeTableInstance().removeMergeCells(merges);
    if (toggleInfoMap.value[key]) {
      merges.forEach((item) => {
        Object.assign(item, { rowspan: rowSpan });
      });
      // 解决收起后，表格底部空白问题
      nextTick(() => {
        tableRef.value.updateTableKey();
      });
    } else {
      // TODO: 收起很慢，怀疑是底层实现有问题
      merges.forEach((item) => {
        if (item.col !== 0) {
          Object.assign(item, { rowspan: 1 });
        }
      });
    }
    tableRef.value.bkTableRef.getVxeTableInstance().setMergeCells(merges);
    toggleInfoMap.value[key] = !toggleInfoMap.value[key];
  };

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData({
      ...searchParams,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      limit: -1,
      offset: 0,
      ordering: 'key',
      type: 'cluster',
    });
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
            <div class='tag'>{t('标签键')}:</div>
            <div class='content'>{Object.keys(selectedMap.value).join(',')}</div>
          </div>
          <div class='tips'>{t('删除后将无法恢复，请谨慎操作')}</div>
        </div>
      ),
      onConfirm: () => {
        const targetKeys = Object.keys(selectedMap.value);
        const ids = tableData.reduce<number[]>((result, item) => {
          if (targetKeys.includes(item.key)) {
            result.push(item.id);
          }
          return result;
        }, []);
        runDelete({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          ids,
        });
      },
      title: t('确认批量删除n个标签键？', { n: Object.keys(selectedMap.value).length }),
      width: 480,
    });
  };

  const handleCreate = () => {
    isCreateTagDialogShow.value = true;
  };

  const handleClose = () => {
    isCreateTagDialogShow.value = false;
  };

  const handleConfirm = () => {
    const inputData = createTagRef.value!.getValue();
    if (!inputData) {
      return;
    }

    const tags = Object.entries(inputData).reduce<
      {
        key: string;
        value: string;
      }[]
    >((results, item) => {
      const [key, valueList] = item;
      valueList.forEach((value) => {
        results.push({
          key,
          value,
        });
      });
      return results;
    }, []);

    runBatchCreate({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      tags,
      type: 'cluster',
    });
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less" scoped>
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

  .cluster-tag-manage-page {
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
  .tag-manage-batch-delete-wrapper {
    .tag-wrapper {
      display: flex;
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

  .append-tag-pop-confirm-main {
    .append-tag-main {
      margin-bottom: 16px;

      .title-main {
        position: relative;

        &::after {
          position: absolute;
          top: 2px;
          left: 40px;
          color: #ea3636;
          content: '*';
        }
      }
    }

    .bk-pop-confirm-title {
      font-size: 16px;
    }

    .bk-pop-confirm-footer {
      button {
        width: 64px;
      }
    }
  }

  .tag-key-column-main {
    display: flex;
    align-items: center;
    cursor: pointer;

    &:hover {
      .append-btn {
        display: block;
      }
    }

    .append-btn {
      display: none;
      margin-left: 16px;

      &.is-always-show {
        display: block;
      }
    }

    .toggle-icon {
      margin-right: 8px;
      transform: rotate(-90deg);

      &.is-open {
        transform: rotate(0deg);
      }
    }
  }

  .bind-cluster-column-main {
    display: flex;
    align-items: center;

    &:hover {
      .copy-icon {
        display: block;
      }
    }

    .copy-icon {
      display: none;
      margin-left: 4px;
      font-size: 12px;
      color: #3a84ff;
      cursor: pointer;
    }
  }

  .delete-tag-pop-confirm-main {
    .delete-tag-main {
      margin-bottom: 12px;
      color: #63656e;

      .content-main {
        display: flex;
        margin-bottom: 4px;
        align-items: center;

        .value-main {
          color: #313238;
        }
      }
    }

    .bk-pop-confirm-title {
      font-size: 16px;
    }

    .bk-pop-confirm-footer {
      button {
        width: 64px;
      }
    }
  }

  .create-tag-dialog-main {
    .bk-modal-wrapper {
      max-height: 30vh;

      .bk-modal-body {
        .bk-modal-content {
          max-height: calc(80vh - 100px) !important;
          overflow-y: auto;
        }
      }

      .footer-wrapper {
        button {
          width: 64px;
        }
      }
    }
  }
</style>
