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
  <DbDialog
    v-model:is-show="isShow"
    class="cluster-batch-add-tag-main"
    :close-icon="false"
    :confirm-button-disable-info="{
      disabled: !selectedClusters.length,
      tooltips: { content: '', disabled: true },
    }"
    :confirm-handler="handleConfirm"
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
            :title="t('为选中集群添加标签，若标签键不存在则新添加，已存在则跳过')" />
          <div class="operation-main">
            <TagOperation
              ref="tagOperationRef"
              :allow-key-value-empty="false"
              @change="checkValidTags" />
          </div>
        </div>
      </template>
      <template #aside>
        <div class="preview-operate-main">
          <div class="title-main">
            <span style="font-weight: 700">{{ t('已选集群') }}：</span>
            <I18nT
              keypath="共 {n} 个，{action} {k}"
              tag="span">
              <template #n>{{ count.n }}</template>
              <template #action>{{ t('添加') }}</template>
              <template #k>{{ count.k }}</template>
            </I18nT>
            <I18nT
              v-if="count.s > 0"
              keypath="，跳过 {s}"
              tag="span">
              <template #s>{{ count.s }}</template>
            </I18nT>
            <I18nT
              v-if="count.a > 0 && count.b > 0"
              keypath="（无权限 {a}，{reason} {b}）"
              tag="span">
              <template #a>{{ count.a }}</template>
              <template #reason>{{ t('同名标签') }}</template>
              <template #b>{{ count.b }}</template>
            </I18nT>
            <I18nT
              v-else-if="count.a > 0"
              keypath="（无权限 {a}）"
              tag="span">
              <template #a>{{ count.a }}</template>
            </I18nT>
            <I18nT
              v-else-if="count.b > 0"
              keypath="（{reason} {b}）"
              tag="span">
              <template #reason>{{ t('同名标签') }}</template>
              <template #b>{{ count.b }}</template>
            </I18nT>
          </div>
          <div class="cluster-list-main">
            <div
              v-for="item in selectedClusters"
              :key="item.id"
              class="cluster-item">
              <div
                v-overflow-tips
                class="cluster-name"
                :class="{ 'is-skip': filterClusterIds.includes(item.id) }">
                {{ item.masterDomain }}
              </div>
              <DbIcon
                class="operate-icon"
                style="font-size: 14px"
                type="copy"
                @click="() => execCopy(item.masterDomain)" />
              <BkTag
                v-if="filterClusterIds.includes(item.id)"
                class="status-icon"
                size="small">
                {{ t('跳过') }}
              </BkTag>
              <BkTag
                v-else
                class="status-icon"
                size="small"
                theme="success">
                {{ t('添加') }}
              </BkTag>

              <!-- <DbIcon
                  class="operate-icon ml-6"
                  style="font-size: 18px"
                  type="close"
                  @click="() => handleRemoveCluster(index)" /> -->
            </div>
          </div>
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <BkButton
        class="mr-8 w-64"
        :disabled="!selectedClusters.length || !isAbleToAddTags"
        theme="primary"
        @click="handleConfirm">
        {{ t('添加') }}
      </BkButton>
      <BkButton
        class="w-64"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbDialog>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { addClusterTagKeys } from '@services/source/dbbase';
  import type { ClusterCommonInfo } from '@services/types';

  import { countBatchOperation, execCopy, messageSuccess } from '@utils';

  import TagOperation from './components/tag-operation/Index.vue';

  interface Props {
    /** 集群是否可编辑（有标签权限），无法判断时默认全部可编辑 */
    getEditable?: (item: { permission?: Record<string, boolean> } & ClusterCommonInfo) => boolean;
    selected?: ClusterCommonInfo[];
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    getEditable: () => true,
    selected: () => [],
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const tagOperationRef = ref<InstanceType<typeof TagOperation>>();
  const selectedClusters = ref<NonNullable<Props['selected']>>([]);
  /** 无权限跳过的集群ID（基于 getEditable 即时计算，打开弹窗即生效） */
  const noPermissionIds = computed(() =>
    selectedClusters.value.filter((item) => !props.getEditable(item)).map((item) => item.id),
  );
  /** 同名标签跳过的集群ID */
  const sameTagIds = ref<number[]>([]);
  const isAbleToAddTags = ref(false);

  /** 统一计数：无权限 a / 同名标签 b / 将提交 k */
  const count = computed(() =>
    countBatchOperation(selectedClusters.value, {
      hasPermission: (item) => props.getEditable(item),
      statusMismatch: (item) => sameTagIds.value.includes(item.id),
    }),
  );

  /** 所有跳过的集群ID（无权限 + 同名标签） */
  const filterClusterIds = computed(() => [...noPermissionIds.value, ...sameTagIds.value]);

  const { runAsync: handleAddClusterTagKeys } = useRequest(addClusterTagKeys, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
      isShow.value = false;
      sameTagIds.value = [];
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

  // const handleRemoveCluster = (index: number) => {
  //   selectedClusters.value.splice(index, 1);
  // };

  const handleClose = () => {
    isShow.value = false;
  };

  const checkValidTags = () => {
    return new Promise<{ clusterIds: number[]; tags: Record<string, string>[] } | null>((resolve) => {
      setTimeout(async () => {
        const tagsInfo = await tagOperationRef.value!.getValue();
        if (!tagsInfo) {
          isAbleToAddTags.value = false;
          resolve(null);
          return;
        }

        sameTagIds.value = [];
        const tags = tagsInfo.map((item) => ({
          [item.key]: item.value,
        }));
        const clusterIdTagsMap = selectedClusters.value.reduce<Record<string, Record<string, string>>>(
          (result, item) => {
            Object.assign(result, {
              [item.id]: item.tags.reduce<Record<string, string>>((tagsResult, tag) => {
                Object.assign(tagsResult, {
                  [tag.key]: tag.value,
                });
                return tagsResult;
              }, {}),
            });
            return result;
          },
          {},
        );
        const tagsKeys = tags.map((tag) => Object.keys(tag)[0]);
        Object.entries(clusterIdTagsMap).forEach(([clusterId, tagsObj]) => {
          if (tagsKeys.every((tagKey) => tagKey in tagsObj)) {
            sameTagIds.value.push(Number(clusterId));
          }
        });
        const clusterIds = selectedClusters.value.map((item) => item.id);
        if (count.value.k === 0) {
          isAbleToAddTags.value = false;
          return null;
        }

        isAbleToAddTags.value = true;
        resolve({
          clusterIds: _.difference(clusterIds, filterClusterIds.value),
          tags,
        });
      });
    });
  };

  const handleConfirm = async () => {
    const result = await checkValidTags();
    if (!result) {
      return;
    }

    const { clusterIds, tags } = result;
    handleAddClusterTagKeys({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_ids: clusterIds,
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
            color: #313238;
            background: #fff;
            border: 1px solid #dcdee5;
            border-radius: 0 2px 2px 0;
            align-items: center;
          }

          .skip-tag-main {
            padding: 0 24px;
            margin-top: 8px;
          }

          .cluster-list-main {
            padding: 0 24px;
            margin: 8px 0 16px;
            overflow-y: auto;
            flex: 1;

            .exception-main {
              .bk-exception-title {
                font-size: 12px;
                color: #63656e;
              }
            }

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
                color: #4d4f56;
                text-overflow: ellipsis;
                white-space: nowrap;
                flex: 1;

                &.is-skip {
                  color: #c4c6cc;
                }
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
