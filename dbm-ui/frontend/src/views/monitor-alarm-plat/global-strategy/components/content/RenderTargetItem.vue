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
  <div
    ref="itemRef"
    v-bk-tooltips="{
      disabled: !isShowToolTip,
      content: list.join(','),
    }"
    class="item">
    {{ titleText }}: {{ list.join(',') }}
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    title?: string;
    list?: string[];
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
    list: () => [],
  });

  const { t } = useI18n();

  const itemRef = ref();
  const isShowToolTip = ref(false);

  const titleMap = {
    appid: t('业务'),
    cluster_domain: t('集群'),
    db_module: t('模块'),
  } as Record<string, string>;

  const titleText = computed(() => (titleMap[props.title] === undefined ? props.title : titleMap[props.title]));

  onMounted(() => {
    isShowToolTip.value = itemRef.value.clientWidth < itemRef.value.scrollWidth;
  });
</script>
<style lang="less" scoped>
  .item {
    width: 100%;
    height: 20px;
    overflow: hidden;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
