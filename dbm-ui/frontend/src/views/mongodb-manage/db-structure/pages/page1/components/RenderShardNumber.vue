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
  <DbFormItem
    :label="t('每台主机构造Shard数量')"
    property="shardNum"
    required>
    <div class="mongo-dbstruct-shard-num">
      <BkInput
        v-model="data"
        :min="1"
        type="number" />
      <span class="need-tip">{{ t('共需n台主机', {n: needHostNum}) }}</span>
    </div>
  </DbFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    needHostNum: number,
  }

  interface Emits {
    (e: 'change', value: number): void
  }

  interface Exposes {
    getValue: () => Promise<number>
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const data = defineModel<number>({
    default: 0,
  });

  const { t } = useI18n();
  const localValue = ref(0);
  const editRef = ref();

  watch(localValue, () => {
    emits('change', Number(localValue.value));
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (Number(localValue.value)));
    },
  });

</script>

<style lang="less">
.mongo-dbstruct-shard-num {
  .bk-input {
    width: 400px;
  }

  .need-tip {
    margin-left: 12px;
    font-size: 12px;
    color: #63656E;
  }
}
</style>
