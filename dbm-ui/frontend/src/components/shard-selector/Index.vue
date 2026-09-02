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
    class="dbm-shard-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    width="80%"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      collapsible
      initial-divide="320px"
      :max="360"
      :min="320"
      placement="right">
      <template #main>
        <div class="shard-selector-table mt-16 mb-16">
          <!-- <DbQuickSearch
            v-model="quickSearchValue"
            class="mt-16 mb-16"
            :data="quickSearchData"
            :placeholder="t('请输入或选择条件搜索')"
            @change="handleQuickSearchChange" /> -->
          <DbTable
            ref="shardTable"
            class="db-shard-table"
            :container-height="570"
            :data-source="getMongoShard"
            :disable-select-method="disableSelectMethod"
            row-key="shard_name"
            selectable
            :selected="modelValue"
            @request-success="handleRequestSuccess"
            @selection="handleSelection">
            <TableColumn
              col-key="shard_name"
              fixed="left"
              :min-width="140"
              :title="t('分片名')" />
            <TableColumn
              col-key="master_domain"
              :min-width="200"
              :title="t('所属集群')" />
            <!-- <TableColumn
              col-key="related_instance"
              :min-width="200"
              :title="t('关联实例')">
              <template #default="{ row }: { row: IRowData }">
                <span
                  v-overflow-tips
                  class="text-overflow">
                  {{ renderRelatedInstances(row) }}
                </span>
              </template>
            </TableColumn>
            <TableColumn
              col-key="region"
              :title="t('地域')"
              :width="120">
              <template #default="{ row }: { row: IRowData }">
                {{ row.region || '--' }}
              </template>
            </TableColumn> -->
          </DbTable>
        </div>
      </template>
      <template #aside>
        <div class="shard-selector-preview-result">
          <div class="header">
            <span>{{ t('结果预览') }}</span>
            <BkDropdown
              class="result-dropdown"
              :popover-options="{
                clickContentAutoHide: true,
              }"
              trigger="click">
              <i class="db-icon-more result-trigger" />
              <template #content>
                <BkDropdownMenu>
                  <BkDropdownItem @click="handleClear">
                    {{ t('清空所有') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopyShards">
                    {{ t('复制所有分片名') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </div>
          <BkException
            v-if="modelValue.length === 0"
            class="mt-50"
            :description="t('暂无数据_请从左侧添加对象')"
            scene="part"
            type="empty" />
          <div
            v-else
            class="result-wrapper db-scroll-y">
            <div
              v-for="(item, index) of modelValue"
              :key="item.shard_name"
              v-test="{ type: 'span', value: 'instanceSelectorPreviewItem' }"
              class="result-item">
              <span
                v-overflow-tips
                class="text-overflow">
                {{ item.shard_name }}
              </span>
              <DbIcon
                type="close result-item-remove"
                @click="handleRemove(index)" />
            </div>
          </div>
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          disabled: modelValue.length > 0,
          content: t('请选择分片'),
        }">
        <BkButton
          class="w-88"
          :disabled="modelValue.length === 0"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml-8 w-88"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getMongoShard } from '@services/source/mongodbToolbox';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { execCopy } from '@utils';

  type IRowData = ServiceReturnType<typeof getMongoShard>['results'][number];

  export interface Props {
    disableSelectMethod?: (data: IRowData) => boolean | string;
  }

  type Emits = {
    (e: 'change', value: IRowData[]): void;
    (e: 'cancel'): void;
  };

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IRowData[]>({
    required: true,
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const shardTableRef = useTemplateRef('shardTable');

  const fetchData = () => {
    shardTableRef.value?.fetchData({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };

  watch(isShow, (show) => {
    if (show) {
      setTimeout(() => {
        fetchData();
      });
    }
  });

  const handleSelection = (_key: string[], list: IRowData[]) => {
    modelValue.value = list;
  };

  // 本次打开时预置的选中态快照
  const openSelection = shallowRef<IRowData[]>([]);

  // DbTable 取数成功后默认会清空整表选中并触发空 selection，
  // 这里在加载完成后恢复本次打开时预置的选中态
  const handleRequestSuccess = () => {
    if (modelValue.value.length === 0 && openSelection.value.length > 0) {
      modelValue.value = openSelection.value;
    }
  };

  const handleRemove = (index: number) => {
    const target = [...modelValue.value];
    target.splice(index, 1);
    modelValue.value = target;
  };

  const handleClear = () => {
    modelValue.value = [];
  };

  const handleCopyShards = () => {
    execCopy(modelValue.value.map((item) => item.shard_name).join('\n'), t('复制成功'));
  };

  // const renderRelatedInstances = (row: IRowData) =>
  //   (row.related_instance || []).map((item) => item.instance).join('，') || '--';

  const handleConfirm = () => {
    emits('change', modelValue.value);
    handleClose();
  };

  const handleCancel = () => {
    emits('cancel');
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .dbm-shard-selector {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }

    .shard-selector-table {
      height: 570px;
      padding: 0 24px;
    }

    .shard-selector-preview-result {
      display: flex;
      height: 100%;
      max-height: 625px;
      padding: 12px 24px;
      overflow: hidden;
      font-size: @font-size-mini;
      background-color: #f5f6fa;
      flex-direction: column;

      .header {
        display: flex;
        padding-bottom: 16px;
        align-items: center;

        > span {
          flex: 1;
          font-size: @font-size-normal;
          color: @title-color;
        }

        .result-dropdown {
          font-size: 0;
          line-height: 20px;
        }

        .result-trigger {
          display: block;
          font-size: 18px;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            background-color: @bg-disable;
            border-radius: 2px;
          }
        }
      }

      .result-wrapper {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow-y: auto;

        .result-item {
          display: flex;
          padding: 0 12px;
          margin-bottom: 2px;
          line-height: 32px;
          background-color: @bg-white;
          border-radius: 2px;
          justify-content: space-between;
          align-items: center;

          .result-item-remove {
            display: none;
            font-size: @font-size-large;
            font-weight: bold;
            color: @gray-color;
            cursor: pointer;

            &:hover {
              color: @default-color;
            }
          }

          &:hover {
            .result-item-remove {
              display: block;
            }
          }
        }
      }
    }
  }
</style>
