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
    class="cluster-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    height="auto"
    :is-show="isShow"
    :quick-close="false"
    title=""
    :width="dialogWidth"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      :initial-divide="400"
      :max="500"
      :min="300"
      placement="right">
      <template #aside>
        <div class="cluster-selector__result">
          <div class="result__title">
            <span>{{ $t('结果预览') }}</span>
            <BkDropdown class="result__dropdown">
              <i class="db-icon-more result__trigger" />
              <template #content>
                <BkDropdownMenu>
                  <BkDropdownItem @click="handleClearSelected">
                    {{ $t('清空所有') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopyCluster">
                    {{ $t('复制所有集群') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </div>
          <ResultPreview
            :selected-map="selectedMap"
            :show-title="showPreviewResultTitle"
            :tab-list="tabList"
            @delete-item="handleSelecteRow" />
        </div>
      </template>
      <template #main>
        <div class="cluster-selector__main">
          <div
            ref="clusterTabsRef"
            class="cluster-selector__tabs">
            <BkPopover
              v-for="tabItem of tabList"
              :key="tabItem.id"
              ref="tabTipsRef"
              :disabled="!showSwitchTabTips"
              theme="light">
              <div
                class="tabs__item"
                :class="[{ 'tabs__item--active': tabItem.id === activeTab }]"
                @click.stop="handleChangeTab(tabItem.id)">
                {{ tabItem.name }}
              </div>
              <template
                #content>
                <div class="tab-tips">
                  <h4>{{ $t('切换类型说明') }}</h4>
                  <p>{{ $t('切换后如果重新选择_选择结果将会覆盖原来选择的内容') }}</p>
                  <BkButton
                    size="small"
                    theme="primary"
                    @click="handleCloseTabTips">
                    {{ $t('我知道了') }}
                  </BkButton>
                </div>
              </template>
            </BkPopover>
          </div>
          <div class="cluster-selector__content">
            <CurrentContent
              :active-tab="activeTab"
              :get-resource-list="getResourceList"
              :selected="selectedArr"
              @change="handleSelectTable" />
          </div>
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <BkButton
        class="cluster-selector__button mr-8"
        :disabled="isEmpty"
        theme="primary"
        @click="handleConfirm">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        class="cluster-selector__button"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx" generic="T extends SpiderModel">
  import { useFormItem } from 'bkui-vue/lib/shared';
  import _ from 'lodash';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SpiderModel from '@services/model/spider/spider';
  import type { ListBase } from '@services/types/common';

  import { useCopy, useSelectorDialogWidth } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import { messageWarn } from '@utils';

  import ResultPreview from './components/ResultPreview.vue';
  import SpiderTable from './components/spider-table/Index.vue';


  interface Props {
    selected: Record<string, T[]>,
    tabList?: { name: string; id: string, content?: Element }[],
    showPreviewResultTitle?: boolean,
    // eslint-disable-next-line vue/no-unused-properties
    getResourceList: (params: Record<string, any>) => Promise<ListBase<T[]>>
  }

  interface Emits {
    (e: 'change', value: SelectedMap): void,
  }

  type ValueOf<T> = T[keyof T]

  type SelectedMap = Props['selected'];

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    selected: () =>  ({}),
    tabList: () => ([
      {
        id: ClusterTypes.SPIDER,
        name: '集群选择',
      },
    ]),
    showPreviewResultTitle: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });


  const copy = useCopy();
  const formItem = useFormItem();
  const { dialogWidth } = useSelectorDialogWidth();

  const tabTipsRef = ref();
  const activeTab = ref(props.tabList[0].id);
  const showTabTips = ref(false);
  const selectedMap = shallowRef<Record<string, Record<string, ValueOf<SelectedMap>[0]>>>({});
  const isSelectedAll = ref(false);

  const contentMap = computed(() => {
    if (props.tabList.length > 1) {
      return props.tabList.reduce((result, item) => {
        if (item.content) {
          // eslint-disable-next-line no-param-reassign
          result[item.id] = item.content;
        }
        return result;
      }, {} as Record<string, Element>);
    }
    if (props.tabList[0].content) {
      return {
        [ClusterTypes.SPIDER]: props.tabList[0].content,
      };
    }
    return {
      [ClusterTypes.SPIDER]: SpiderTable,
    };
  });

  const CurrentContent = computed(() => (contentMap.value as unknown as Record<string, Element>)[activeTab.value]);

  const selectedArr = computed(() => (Object.keys(selectedMap.value).length > 0
    ? ({ [activeTab.value]: Object.values(selectedMap.value[activeTab.value]) }) :  {}));

  // 显示切换 tab tips
  const showSwitchTabTips = computed(() => showTabTips.value && props.tabList.length > 1);
  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(selectedMap.value), item => Object.keys(item).length < 1));


  watch(isShow, (show) => {
    if (show) {
      selectedMap.value = props.tabList.map(({ id }) => id).reduce((result, tabKey) => {
        if (!props.selected[tabKey]) {
          return result;
        }
        const tabSelectMap = props.selected[tabKey].reduce((selectResult, selectItem) => ({
          ...selectResult,
          [selectItem.id]: selectItem,
        }), {} as Record<string, ValueOf<SelectedMap>[0]>);
        return {
          ...result,
          [tabKey]: tabSelectMap,
        };
      }, {} as Record<string, Record<string, ValueOf<SelectedMap>[0]>>);
      showTabTips.value = true;
    }
  });

  /**
   * 切换 tab
   */
  const handleChangeTab = (id: string) => {
    if (activeTab.value === id) {
      return;
    }
    activeTab.value = id;
  };
  /**
   * 关闭提示
   */

  const handleCloseTabTips = () => {
    showTabTips.value = false;
    if (tabTipsRef.value) {
      for (const ref of tabTipsRef.value) {
        ref.hide();
      }
    }
  };


  /**
   * 清空选中项
   */
  const handleClearSelected = () => {
    selectedMap.value = {};
    isSelectedAll.value = false;
  };

  /**
   * 复制集群域名
   */

  function handleCopyCluster() {
    const copyValues = Object.values(selectedMap.value).reduce((result, selectItem) => {
      result.push(...Object.values(selectItem).map(item => item.master_domain));
      return result;
    }, [] as string[]);

    if (copyValues.length < 1) {
      messageWarn(t('没有可复制集群'));
      return;
    }

    copy(copyValues.join('\n'));
  }

  function handleConfirm() {
    const result = Object.keys(selectedMap.value).reduce((result, tabKey) => ({
      ...result,
      [tabKey]: Object.values(selectedMap.value[tabKey]),
    }), {});
    emits('change', result);
    nextTick(() => {
      formItem?.validate?.('change');
      formItem?.validate?.('blur');
    });
    handleClose();
  }

  function handleClose() {
    isShow.value =  false;
  }

  /**
   * 选择当行数据
   */
  const handleSelecteRow = (data: ValueOf<SelectedMap>[0], value: boolean) => {
    const selectedMapMemo = { ...selectedMap.value };
    if (!selectedMapMemo[activeTab.value]) {
      selectedMapMemo[activeTab.value] = {};
    }
    if (value) {
      selectedMapMemo[activeTab.value][data.id] = data;
    } else {
      delete selectedMapMemo[activeTab.value][data.id];
    }
    selectedMap.value = selectedMapMemo;
  };

  const handleSelectTable = (selected: Record<string, Record<string, ValueOf<SelectedMap>[0]>>) => {
    selectedMap.value = selected;
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .cluster-selector {
    font-size: @font-size-mini;

    :deep(.bk-modal-header) {
      display: none;
    }

    :deep(.bk-modal-content) {
      padding: 0;
    }

    &__tabs {
      height: 42px;
      font-size: @font-size-mini;
      line-height: 42px;
      background-color: #fafbfd;
      border-bottom: 1px solid @border-disable;
      .flex-center();

      .tabs__item {
        min-width: 200px;
        margin-bottom: -1px;
        text-align: center;
        cursor: pointer;
        border: 1px solid @border-disable;
        border-top: 0;
        border-left: 0;
        border-bottom-color: transparent;

        &--active {
          background-color: @bg-white;
          border-bottom-color: @border-white;
        }
      }
    }

    &__content {
      height: 585px;
      padding: 16px 24px 0;

      :deep(.bk-pagination-small-list) {
        order: 3;
        flex: 1;
        justify-content: flex-end;
      }
    }

    &__result {
      height: 100%;
      padding: 12px 24px;
      font-size: @font-size-mini;
      background-color: #f5f6fa;

      .result__title {
        padding-bottom: 16px;
        .flex-center();

        > span {
          flex: 1;
          font-size: @font-size-normal;
          color: @title-color;
        }

        .result__dropdown {
          font-size: 0;
          line-height: 20px;
        }

        .result__trigger {
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

      .result__item {
        padding: 0 12px;
        margin-bottom: 2px;
        line-height: 32px;
        background-color: @bg-white;
        border-radius: 2px;
        justify-content: space-between;
        .flex-center();

        .result__remove {
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
          .result__remove {
            display: block;
          }
        }
      }
    }

    &__button {
      width: 88px;
    }
  }

  .tab-tips {
    padding: 9px 0 17px;
    color: @default-color;
    text-align: right;

    h4 {
      font-size: @font-size-large;
      font-weight: normal;
      color: @title-color;
      text-align: left;
    }

    p {
      padding: 8px 0 16px;
      text-align: left;
    }
  }
</style>
