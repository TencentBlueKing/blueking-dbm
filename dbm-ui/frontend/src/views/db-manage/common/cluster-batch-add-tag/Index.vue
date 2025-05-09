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
          <div class="header-main">{{ t('批量添加标签') }}</div>
          <BkAlert
            class="alert-tip"
            closable
            theme="warning"
            :title="t('为集群添加标签，若标签键存在则新添加，已存在则忽略')" />
          <div class="operation-main">
            <TagOperation
              ref="tagOperationRef"
              :allow-key-value-empty="false" />
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
      <BkButton
        class="mr-8 w-64"
        :disabled="!selectedClusters.length"
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
    </template>
  </BkDialog>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { addClusterTagKeys } from '@services/source/dbbase';
  import type { ClusterCommonInfo } from '@services/types';

  import { execCopy, messageSuccess } from '@utils';

  import TagOperation from './components/tag-operation/Index.vue';

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

  const tagOperationRef = ref<InstanceType<typeof TagOperation>>();
  const selectedClusters = ref<NonNullable<Props['selected']>>([]);

  const { loading: confirmLoading, run: handleAddClusterTagKeys } = useRequest(addClusterTagKeys, {
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
      }
    },
    {
      immediate: true,
    },
  );

  const handleRemoveCluster = (index: number) => {
    selectedClusters.value.splice(index, 1);
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = async () => {
    const tagsInfo = await tagOperationRef.value!.getValue();
    if (!tagsInfo) {
      return;
    }

    const tags = Object.values(tagsInfo).map((item) => item.value) as number[];
    handleAddClusterTagKeys({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_ids: selectedClusters.value.map((item) => item.id),
      tags,
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
            margin: 12px 24px 16px;
          }

          .operation-main {
            padding: 0 24px;
            overflow-y: auto;
            flex: 1;
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
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }

              .operate-icon {
                display: none;
                color: #1768ef;
              }
            }
          }
        }
      }
    }
  }
</style>
