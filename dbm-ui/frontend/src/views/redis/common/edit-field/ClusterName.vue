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
  <div class="cluster-name-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="t('请输入或选择集群')"
      :rules="rules"
      @submit="handleInputFinish" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getRedisList } from '@services/source/redis';

  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    data?: string;
    inputed?: string[];
  }

  interface Emits {
    (e: 'inputFinish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: (isSubmit?: boolean) => Promise<string>;
  }

  type RedisModel = ServiceReturnType<typeof getRedisList>['results'][number];

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(props.data);
  const editRef = ref();

  let isSkipInputFinish = false;

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: async (value: string) => {
        const listResult = await getRedisList({ exact_domain: value });
        if (listResult.results.length && !isSkipInputFinish) {
          emits('inputFinish', listResult.results[0]);
        }
        return listResult.results.length > 0;
      },
      message: t('目标集群不存在'),
    },
    {
      validator: (value: string) => props.inputed.filter((item) => item === value).length < 2,
      message: t('目标集群重复'),
    },
  ];

  watch(
    () => props.data,
    (data) => {
      localValue.value = data;
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = () => {
    isSkipInputFinish = false;
  };

  defineExpose<Exposes>({
    getValue(isSubmit = false) {
      isSkipInputFinish = isSubmit;
      return editRef.value.getValue().then(() => localValue.value);
    },
  });
</script>

<style lang="less" scoped>
  .cluster-name-box {
    position: relative;

    .edit-btn {
      position: absolute;
      top: 0;
      right: 5px;
      z-index: -1;
      display: flex;
      width: 24px;
      height: 40px;
      align-items: center;

      .edit-btn-inner {
        display: flex;
        width: 24px;
        height: 40px;
        align-items: center;

        .edit-btn-inner {
          display: flex;
          width: 24px;
          height: 24px;
          cursor: pointer;
          border-radius: 2px;
          align-items: center;
          justify-content: center;

          .select-icon {
            font-size: 16px;
            color: #979ba5;
          }

          &:hover {
            background: #f0f1f5;

            .select-icon {
              color: #3a84ff;
            }
          }
        }
      }
    }
  }
</style>
