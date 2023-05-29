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
  <div class="render-cluster-role">
    <template v-if="data.length < 1">
      --
    </template>
    <template v-else>
      <BkTag
        v-for="item in renderList"
        :key="item">
        {{ item }}
      </BkTag>
    </template>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: Array<string>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const codeMap = {
    Cold: t('冷节点'),
    Hot: t('热节点'),
  } as Record<string, string>;

  const renderList = computed(() => props.data.map((item) => {
    const word = _.last(item.split('_'));
    const code = `${word?.charAt(0).toUpperCase()}${word?.slice(1)}`;
    return codeMap[code] ? codeMap[code] : code;
  }));
</script>
<style lang="less">
  .render-cluster-role {
    display: block;
  }
</style>
