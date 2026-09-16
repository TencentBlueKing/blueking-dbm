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
        <div class="shard-selector-tabs">
          <div class="tabs-item">{{ t('分片') }}</div>
        </div>
        <div class="shard-selector-table">
          <DbQuickSearch
            v-model="quickSearchValue"
            class="mt-16 mb-16"
            :data="quickSearchData"
            @change="handleQuickSearchChange" />
          <DbTable
            ref="shardTable"
            class="db-shard-table"
            :container-height="containerHeight"
            :data-source="getMongoShard"
            :disable-select-method="handleDisableSelect"
            row-click-selectable
            row-key="shard_name"
            selectable
            :selected="localSelected"
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
            <TableColumn
              col-key="related_instance"
              :min-width="200"
              :title="t('关联实例')">
              <template #default="{ row }: { row: IRowData }">
                <div
                  v-if="row.related_instance?.length"
                  class="related-instance-list">
                  <div
                    v-for="item in row.related_instance"
                    :key="item.bk_instance_id"
                    v-overflow-tips
                    class="text-overflow">
                    {{ item.instance }}
                  </div>
                </div>
                <span v-else>--</span>
              </template>
            </TableColumn>
            <TableColumn
              col-key="region"
              :title="t('地域')"
              :width="120">
              <template #default="{ row }: { row: IRowData }">
                {{ row.region || '--' }}
              </template>
            </TableColumn>
          </DbTable>
        </div>
      </template>
      <template #aside>
        <div class="shard-selector-result">
          <div class="result-title">
            <DbIcon
              class="mr-4"
              type="legend" />
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
          <div class="result-content db-scroll-y">
            <BkException
              v-if="isEmpty"
              class="mt-50"
              :description="t('暂无数据_请从左侧添加对象')"
              scene="part"
              type="empty" />
            <CollapseMini
              v-else
              :count="localSelected.length"
              :title="t('分片')">
              <div
                v-for="item of localSelected"
                :key="item.shard_name"
                v-test="{ type: 'span', value: 'instanceSelectorPreviewItem' }"
                class="result-item">
                <span
                  v-overflow-tips
                  class="text-overflow">
                  {{ item.shard_name }}
                </span>
                <div class="result-operations">
                  <i
                    class="db-icon-copy result-copy"
                    @click="execCopy(item.shard_name)" />
                  <i
                    class="db-icon-close result-remove"
                    @click="handleRemove(item)" />
                </div>
              </div>
            </CollapseMini>
          </div>
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          disabled: !isEmpty,
          content: t('请选择分片'),
        }">
        <BkButton
          class="w-88"
          :disabled="isEmpty"
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

  import CollapseMini from './components/CollapseMini.vue';

  type IRowData = ServiceReturnType<typeof getMongoShard>['results'][number];

  export interface Props {
    // 第二个参数是弹窗内当前的选中态，跨集群禁选这类规则要基于它判断，不能读外部已提交的值
    disableSelectMethod?: (data: IRowData, selected: IRowData[]) => boolean | string;
  }

  type Emits = {
    (e: 'change', value: IRowData[]): void;
    (e: 'cancel'): void;
  };

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  // 只作为回填数据源读取，选择结果通过 change 事件提交
  const modelValue = defineModel<IRowData[]>({
    required: true,
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const containerHeight = 570 - 32 - 16; // 去除搜索框的高度和margin bottom

  const shardTableRef = useTemplateRef('shardTable');
  // 弹窗内的勾选走副本，点取消可丢弃
  const localSelected = shallowRef<IRowData[]>([]);

  const isEmpty = computed(() => localSelected.value.length === 0);

  const handleDisableSelect = (data: IRowData) => props.disableSelectMethod?.(data, localSelected.value) ?? false;

  // 接口只支持 shard_names 过滤（逗号分隔、精确匹配），其余条件后端会忽略
  const quickSearchData = [
    {
      id: 'shard_names',
      name: t('分片名'),
      type: 'multiple-input' as const,
    },
  ];

  const quickSearchValue = ref<Record<string, string>>({});

  const fetchData = () => {
    shardTableRef.value?.fetchData({
      ...quickSearchValue.value,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  // 不在打开时重新取数：DbTable 非首次取数会清空整表选中并回吐空 selection，把回填冲掉。
  // 列表数据由 DbQuickSearch 挂载时的回显拉取一次即可
  watch(isShow, (show) => {
    if (show) {
      localSelected.value = [...modelValue.value];
    }
  });

  const handleSelection = (_key: string[], list: IRowData[]) => {
    localSelected.value = list;
  };

  const handleRemove = (item: IRowData) => {
    localSelected.value = localSelected.value.filter((cur) => cur.shard_name !== item.shard_name);
  };

  const handleClear = () => {
    localSelected.value = [];
  };

  const handleCopyShards = () => {
    execCopy(localSelected.value.map((item) => item.shard_name).join('\n'), t('复制成功'));
  };

  const handleConfirm = () => {
    emits('change', localSelected.value);
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

    .shard-selector-tabs {
      display: flex;

      // 只有一个固定 tab，恒为选中态，不给 cursor: pointer 免得看着像能切换
      .tabs-item {
        display: flex;
        height: 40px;
        background-color: #fff;
        border-bottom: 1px solid transparent;
        justify-content: center;
        align-items: center;
        flex: 1;
      }
    }

    .shard-selector-table {
      height: 570px;
      padding: 0 24px;

      .related-instance-list {
        padding: 6px 0;

        .text-overflow {
          line-height: 18px;
        }
      }
    }

    .shard-selector-result {
      display: flex;
      height: 100%;
      overflow: hidden;
      font-size: @font-size-mini;
      background-color: #f5f6fa;
      flex-direction: column;

      .result-title {
        display: flex;
        height: 40px;
        padding: 12px 24px;
        font-weight: bold;
        background-color: @bg-white;
        align-items: center;

        > span {
          flex: 1;
          font-size: @font-size-mini;
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

      .result-content {
        flex: 1;
        padding: 12px 24px;
        overflow-y: auto;
      }

      .result-item {
        display: flex;
        padding: 0 12px;
        margin-bottom: 2px;
        line-height: 32px;
        background-color: @bg-white;
        border-radius: 2px;
        justify-content: space-between;
        align-items: center;

        &:hover {
          background: #e1ecff;

          .result-copy,
          .result-remove {
            display: block;
          }
        }

        .result-operations {
          display: flex;
          gap: 6px;
          align-items: center;
        }

        .result-copy {
          display: none;
          font-size: @font-size-mini;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            color: @primary-color;
          }
        }

        .result-remove {
          display: none;
          font-size: @font-size-large;
          font-weight: bold;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            color: @default-color;
          }
        }
      }
    }
  }
</style>
