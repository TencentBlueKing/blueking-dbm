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
  <BkLoading :loading="isLoading">
    <div class="table-edit-select">
      <div
        v-if="errorMessage"
        class="select-error">
        <DbIcon
          v-bk-tooltips="errorMessage"
          type="exclamation-fill" />
      </div>
      <BkSelect
        v-model="localValue"
        auto-focus
        class="select-box"
        :class="{ 'is-error': Boolean(errorMessage) }"
        :clearable="false"
        :disabled="disabled"
        filterable
        :input-search="false"
        multiple
        :placeholder="t('请选择IP')"
        @change="handleSelect">
        <BkOption
          v-for="(item, index) in ipSelectList"
          :id="item.value"
          :key="index"
          v-bk-tooltips="{
            disabled: !item.disabled,
            content: item.tip,
            placement: 'top',
          }"
          :disabled="item.disabled"
          :name="item.label">
          <div class="spec-display">
            <DbStatus :theme="item.status === 'running' ? 'success' : 'danger'" />
            <span class="text-overflow">{{ item.label }}</span>
            <span>{{ item.bk_city ? `(${item.bk_city})` : '' }}</span>
          </div>
        </BkOption>
      </BkSelect>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';
  import useValidtor from '@components/render-table/hooks/useValidtor';

  type IKey = string | number;

  export interface IListItem {
    value: IKey;
    label: string;
    status: string;
    disabled: boolean;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_city: string;
    bk_sub_zone_id: number;
    tip?: string;
  }

  interface Props {
    selectList: IListItem[];
    isLoading: boolean;
    disabled: boolean;
    isCheckAffinity: boolean;
    max?: number;
  }

  interface Exposes {
    getValue: () => Promise<{
      reduce_nodes: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      }[];
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const localValue = ref<string[]>([]);

  const ipSelectList = computed(() => {
    if (!props.max) {
      return [];
    }
    if (localValue.value.length === props.max) {
      return props.selectList.map((item) => {
        Object.assign(item, {
          disabled: !localValue.value.includes(item.value as string),
          tip: t('只能选择n台', { n: props.max }),
        });
        return item;
      });
    }
    return props.selectList.map((item) => {
      Object.assign(item, {
        disabled: false,
      });
      return item;
    });
  });

  const rules = [
    {
      validator: (list: string[]) => list.length > 0,
      message: t('IP不能为空'),
    },
    {
      validator: (list: string[]) => list.length === props.max,
      message: t('必须缩容n台主机', { n: props.max }),
    },
    {
      validator: (list: string[]) => {
        if (!props.isCheckAffinity) {
          return true;
        }
        const zoneIdSet = new Set<number>();
        props.selectList.forEach((item) => {
          if (!list.includes(item.value as string)) {
            // 未选中
            zoneIdSet.add(item.bk_sub_zone_id);
          }
        });
        return zoneIdSet.size > 1;
      },
      message: t('当前集群容灾要求跨机房'),
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  watch(
    () => props.max,
    () => {
      if (props.max && localValue.value.length > props.max) {
        localValue.value.length = props.max;
      }
    },
  );

  // 选择
  const handleSelect = (value: string[]) => {
    localValue.value = value;
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(() => {
        const hostMap = props.selectList.reduce(
          (results, item) => {
            Object.assign(results, {
              [item.value]: {
                bk_cloud_id: item.bk_cloud_id,
                bk_host_id: item.bk_host_id,
              },
            });
            return results;
          },
          {} as Record<
            string,
            {
              bk_cloud_id: number;
              bk_host_id: number;
            }
          >,
        );
        return {
          reduce_nodes: localValue.value.map((ip) => ({
            ip,
            bk_cloud_id: hostMap[ip].bk_cloud_id,
            bk_host_id: hostMap[ip].bk_host_id,
          })),
        };
      });
    },
  });
</script>
<style lang="less" scoped>
  .is-error {
    :deep(input) {
      background-color: #fff0f1;
      border-radius: 0;
    }

    :deep(.angle-up) {
      display: none !important;
    }
  }

  .table-edit-select {
    position: relative;
    display: flex;
    height: 42px;
    overflow: hidden;
    color: #63656e;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s;
    align-items: center;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

    :deep(.select-box) {
      width: 100%;
      height: 100%;
      padding: 0;
      background: transparent;
      border: none;
      outline: none;

      .bk-select-trigger {
        height: 100%;

        .bk-input {
          height: 100%;
          background: transparent;
          border: none;
        }
      }
    }

    .select-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 9999;
      display: flex;
      padding-right: 6px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }

  .spec-display {
    display: flex;
    width: 100%;
    align-items: center;
  }

  .bk-select-option {
    &.is-selected {
      .count {
        color: white;
        background-color: #a3c5fd;
      }
    }
  }
</style>
