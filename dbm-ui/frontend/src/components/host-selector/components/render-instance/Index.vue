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
  <div class="instance-renderer">
    <div
      v-for="item in displayList"
      :key="item.instance"
      class="instance-renderer-item">
      <DbStatus :theme="item.theme" />
      <TextOverflowLayout>
        <span>{{ item.instance }}</span>
      </TextOverflowLayout>
    </div>
    <BkButton
      v-if="data.length > 3"
      class="ml-20"
      text
      theme="primary"
      @click.stop="showAll = !showAll">
      {{ showAll ? t('收起') : t('更多') }}
      <DbIcon
        class="show-all-icon"
        :type="showAll ? 'up-big' : 'down-big'" />
    </BkButton>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    data: {
      instance: string;
      status: string;
    }[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const showAll = ref(false);

  const getStatusInfo = (status: string) => (status === 'running' ? 'success' : 'danger');

  // 默认只展示 3 条，其余通过「更多」展开
  const displayList = computed(() => {
    const formatDataList = props.data.map((dataItem) => ({
      ...dataItem,
      theme: getStatusInfo(dataItem.status),
    }));
    return showAll.value ? formatDataList : formatDataList.slice(0, 3);
  });
</script>

<style lang="less" scoped>
  .instance-renderer {
    padding: 6px 0;

    .instance-renderer-item {
      display: flex;
      align-items: center;
      gap: 4px;
      line-height: 18px;

      > :last-child {
        flex: 1;
        min-width: 0;
      }
    }

    .show-all-icon {
      margin-left: 2px;
      font-size: 16px;
    }
  }
</style>
