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
  <BkDialog
    class="cluster-batch-add-tag-main"
    :close-icon="false"
    :is-show="isShow"
    :quick-close="false"
    render-directive="if"
    :width="1000"
    @closed="handleClose"
    @confirm="handleConfirm">
    <BkResizeLayout
      :border="false"
      collapsible
      :initial-divide="360"
      :max="500"
      :min="360"
      placement="right"
      style="height: 550px">
      <template #main>
        <div class="tag-operation-main">
          <div class="header-main">{{ t('批量移除标签') }}</div>
          <BkAlert
            class="alert-tip"
            closable
            theme="warning"
            :title="t('移除指定标签，不存在的标签直接忽略')" />
          <div class="search-main">
            <div class="search-title">{{ t('请选择要移除的标签') }}</div>
            <BkInput
              v-model="searchValue"
              class="search-input"
              clearable
              type="search"
              @clear="handleClear"
              @enter="handleSearch" />
          </div>
          <div class="operation-main">
            <BkCheckboxGroup v-model="checkboxGroupValue">
              <BkCheckbox
                v-for="(item, index) in tagList"
                :key="index"
                :disabled="isCheckAll"
                :label="item" />
            </BkCheckboxGroup>
          </div>
        </div>
      </template>
      <template #aside>
        <div class="preview-operate-main">
          <div class="title-main">
            <span>{{ t('已选集群') }}</span>
            【
            <I18nT
              keypath="共n个"
              tag="span">
              <span style="color: #3a84ff">{{ selectedClusters.length }}</span>
            </I18nT>
            】
          </div>
          <div class="cluster-list-main">
            <div
              v-for="(item, index) in selectedClusters"
              :key="item.id"
              class="cluster-item">
              <div
                v-overflow-tips
                class="cluster-name">
                {{ item.masterDomain }}
              </div>
              <DbIcon
                class="operate-icon"
                style="font-size: 14px"
                type="copy"
                @click="() => execCopy(item.masterDomain)" />
              <DbIcon
                class="operate-icon ml-6"
                style="font-size: 18px"
                type="close"
                @click="() => handleRemoveCluster(index)" />
            </div>
          </div>
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <div class="batch-remove-tag-footer-wrapper">
        <BkCheckbox v-model="isCheckAll">{{ t('移除全部标签') }}</BkCheckbox>
        <div>
          <BkButton
            class="mr-8 w-64"
            :disabled="!checkboxGroupValue.length && !isCheckAll"
            :loading="confirmLoading"
            theme="primary"
            @click="handleConfirm">
            {{ t('确定') }}
          </BkButton>
          <BkButton
            class="w-64"
            @click="handleClose">
            {{ t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { removeClusterTagKeys } from '@services/source/dbbase';
  import type { ClusterCommonInfo } from '@services/types';

  import { encodeRegexp, execCopy, messageSuccess } from '@utils';

  interface Props {
    selected: ClusterCommonInfo[];
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  let tagListRaw: string[] = [];

  const searchValue = ref('');
  const checkboxGroupValue = ref<string[]>([]);
  const selectedClusters = ref<NonNullable<Props['selected']>>([]);
  const tagList = ref<string[]>([]);
  const isCheckAll = ref(false);

  const { loading: confirmLoading, run: handleRemoveClusterTagKeys } = useRequest(removeClusterTagKeys, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
      isShow.value = false;
    },
  });

  watch(
    () => props.selected,
    () => {
      if (props.selected.length) {
        selectedClusters.value = props.selected;
        const tagsMap = props.selected
          .map((item) => item.tags)
          .flat()
          .reduce<Record<string, boolean>>((results, item) => {
            Object.assign(results, { [item.key]: true });
            return results;
          }, {});
        tagList.value = Object.keys(tagsMap);
        tagListRaw = tagList.value;
      }
    },
    {
      immediate: true,
    },
  );

  watch(isCheckAll, () => {
    if (isCheckAll.value) {
      checkboxGroupValue.value = [];
    }
  });

  const handleSearch = () => {
    const searchRegex = new RegExp(encodeRegexp(searchValue.value.toLowerCase()), 'i');
    tagList.value = tagListRaw.filter((item) => searchRegex.test(item));
  };

  const handleClear = () => {
    tagList.value = tagListRaw;
  };

  const handleRemoveCluster = (index: number) => {
    selectedClusters.value.splice(index, 1);
  };

  const handleClose = () => {
    searchValue.value = '';
    isCheckAll.value = false;
    handleClear();
    isShow.value = false;
  };

  const handleConfirm = () => {
    handleRemoveClusterTagKeys({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_ids: selectedClusters.value.map((item) => item.id),
      keys: isCheckAll.value ? tagListRaw : checkboxGroupValue.value,
    });
  };
</script>
<style lang="less">
  .cluster-batch-add-tag-main {
    .bk-modal-wrapper {
      .bk-modal-body {
        .bk-modal-header {
          display: none;
        }

        .bk-dialog-content {
          padding: 0;
          margin: 0;
        }

        .tag-operation-main {
          display: flex;
          height: 100%;
          padding: 16px 0;
          flex-direction: column;
          overflow: hidden;

          .header-main {
            padding: 0 24px;
            font-size: 20px;
          }

          .alert-tip {
            margin: 12px 24px;
          }

          .search-main {
            display: flex;
            padding: 0 24px;
            margin-bottom: 12px;
            justify-content: space-between;

            .search-title {
              font-weight: 700;
            }

            .search-input {
              width: 240px;
            }
          }

          .operation-main {
            padding: 0 24px;
            overflow-y: auto;
            flex: 1;

            .bk-checkbox-group {
              display: flex;
              flex-wrap: wrap;

              .bk-checkbox {
                width: 33%;
                margin: 0 0 20px;
              }
            }
          }
        }

        .preview-operate-main {
          display: flex;
          height: 100%;
          font-size: 12px;
          flex-direction: column;
          background-color: #f5f6fa;

          .title-main {
            display: flex;
            height: 40px;
            padding-left: 24px;
            font-weight: 700;
            background: #fff;
            border: 1px solid #dcdee5;
            border-radius: 0 2px 2px 0;
            align-items: center;
          }

          .cluster-list-main {
            padding: 0 24px;
            margin: 16px 0;
            overflow-y: auto;
            flex: 1;

            .cluster-item {
              display: flex;
              width: 100%;
              height: 32px;
              padding: 0 12px;
              margin-bottom: 2px;
              cursor: pointer;
              background: #fff;
              border-radius: 2px;
              align-items: center;

              &:hover {
                background-color: #e1ecff;

                .operate-icon {
                  display: block;
                }
              }

              .cluster-name {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                flex: 1;
              }

              .operate-icon {
                display: none;
                color: #1768ef;
              }
            }
          }
        }

        .batch-remove-tag-footer-wrapper {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
      }
    }
  }
</style>
