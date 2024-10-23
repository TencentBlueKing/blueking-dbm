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
  <div class="selector-panel-tab">
    <BkPopover
      v-for="item in panelList"
      :key="item.id"
      ref="tabTipsRef"
      theme="light">
      <div
        class="tab-item"
        :class="{
          active: modelValue === item.id,
        }"
        @click.stop="handleClick(item)">
        {{ item.name }}
      </div>
      <template #content>
        <div class="tab-tips">
          <h4>{{ t('切换类型说明') }}</h4>
          <p>{{ t('切换后如果重新选择_选择结果将会覆盖原来选择的内容') }}</p>
          <BkButton
            size="small"
            theme="primary"
            @click="handleCloseTabTips">
            {{ t('我知道了') }}
          </BkButton>
        </div>
      </template>
    </BkPopover>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    tabList: {
      id: string;
      name: string;
    }[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const tabTipsRef = ref();

  const panelList = computed(() => [
    ...props.tabList,
    // {
    //   id: 'manual',
    //   name: t('手动输入'),
    // },
  ]);

  const handleClick = (tab: Props['tabList'][number]) => {
    if (modelValue.value === tab.id) {
      return;
    }
    modelValue.value = tab.id;
  };

  /**
   * 关闭提示
   */
  const handleCloseTabTips = () => {
    if (tabTipsRef.value) {
      for (const ref of tabTipsRef.value) {
        ref.hide();
      }
    }
  };
</script>
<style lang="less">
  .selector-panel-tab {
    display: flex;

    .tab-item {
      display: flex;
      height: 40px;
      cursor: pointer;
      background-color: #fafbfd;
      border-bottom: 1px solid #dcdee5;
      justify-content: center;
      align-items: center;
      flex: 1;

      &.active {
        background-color: #fff;
        border-bottom-color: transparent;
      }

      & ~ .tab-item {
        border-left: 1px solid #dcdee5;
      }
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
