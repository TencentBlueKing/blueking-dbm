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
    <div
      class="render-role-box"
      :class="{
        'default-display': data.length === 0,
        'is-error': Boolean(errorMessage)
      }">
      <span
        v-if="data.length === 0"
        style="color: #c4c6cc;">
        {{ $t('输入主库后自动生成') }}
      </span>
      <template v-else>
        <div
          v-for="instance in data"
          :key="instance">
          {{ instance }}
        </div>
      </template>
      <div
        v-if="errorMessage"
        class="input-error">
        <DbIcon
          v-bk-tooltips="errorMessage"
          type="exclamation-fill" />
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['masters'];
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<void>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ([]),
    isLoading: false,
  });

  const { t } = useI18n();

  const errorMessage = ref('');

  defineExpose<Exposes>({
    getValue() {
      if (props.data.length === 0) {
        errorMessage.value = t('不能为空');
      }
      return Promise.resolve();
    },
  });

</script>
<style lang="less" scoped>

.is-error {
  background-color: #fff0f1 !important;
}

.render-role-box {
  position: relative;
  min-height: 42px;
  padding: 10px 16px;
  overflow: hidden;
  line-height: 20px;
  color: #63656e;
  text-overflow: ellipsis;
  white-space: nowrap;

  .input-error {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    display: flex;
    padding-right: 10px;
    font-size: 14px;
    color: #ea3636;
    align-items: center;
  }
}

.default-display {
  cursor: not-allowed;
  background: #FAFBFD;
}
</style>
