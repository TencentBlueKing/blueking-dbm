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
  <div class="instance-selector-preview-result">
    <div class="header">
      <span>{{ $t('结果预览') }}</span>
      <BkDropdown class="result__dropdown">
        <i class="db-icon-more result__trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleClear">
              {{ $t('清空所有') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyInstances">
              {{ $t('复制所有实例') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
    <BkException
      v-if="isEmpty"
      class="mt-50"
      :description="$t('暂无数据_请从左侧添加对象')"
      scene="part"
      type="empty" />
    <div
      v-else
      class="result-wrapper db-scroll-y">
      <template
        v-for="key in keys"
        :key="key">
        <CollapseMini
          v-if="lastValues[key].length > 0"
          collapse
          :count="lastValues[key].length"
          :title="textMap[key]">
          <div
            v-for="(item, index) of lastValues[key]"
            :key="item.ip"
            class="result-item">
            <span
              v-overflow-tips
              class="text-overflow">
              {{ item.ip }}
              <span class="result-item-role">({{ firstLetterToUpper(item.role) }})</span>
            </span>
            <DbIcon
              type="close result-item-remove"
              @click="handleRemove(key, index)" />
          </div>
        </CollapseMini>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  import { firstLetterToUpper } from '@views/redis/common/utils';

  import { messageWarn } from '@utils';

  import { textMap } from '../common/utils';
  import CollapseMini from '../components/CollapseMini.vue';
  import type { ChoosedItem } from '../components/RenderRedisHost.vue';
  import type { InstanceSelectorValues } from '../Index.vue';

  interface Props {
    lastValues: InstanceSelectorValues;
  }

  type Keys = keyof InstanceSelectorValues;

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();

  const keys = computed(() => Object.keys(props.lastValues) as Keys[]);
  const isEmpty = computed(() => !keys.value.some(key => props.lastValues[key].length > 0));

  const handleClear = () => {
    emits('change', {
      idleHosts: [],
    });
  };

  const handleRemove = (key: Keys, index: number) => {
    const target = props.lastValues[key];
    target.splice(index, 1);
    emits('change', {
      ...props.lastValues,
      [key]: target,
    });
  };

  /**
   * 复制集群域名
   */
  const handleCopyInstances = () => {
    if (isEmpty.value) {
      messageWarn(t('没有可复制实例'));
      return;
    }

    const instances: ChoosedItem[] = [];
    for (const key of keys.value) {
      instances.push(...props.lastValues[key]);
    }
    copy(instances.map(item => item.ip).join('\n'));
  };
</script>
<style lang="less">
.instance-selector-preview-result {
  height: 100%;
  max-height: 640px;
  padding: 12px 24px;
  font-size: @font-size-mini;
  background-color: #f5f6fa;

  .header {
    display: flex;
    padding-bottom: 16px;
    align-items: center;

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

  .result-wrapper {
    display: flex;
    flex-direction: column;
    height: calc(100% - 38px);

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

.result-item-role {
  margin-left: 8px;
  font-family: AlTarikh;
  font-size: 12px;
  color: #C4C6CC;
}
</style>
