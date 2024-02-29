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
  <div class="dumper-render-list">
    <div class="instances-view-header">
      <DbIcon
        v-if="activeGroup?.id"
        class="instances-view-header-icon mr-6"
        type="folder-open" />
      <DbIcon
        v-else
        class="instances-view-header-icon mr-6"
        type="summation" />
      <strong>{{ activeGroup?.name || t('全部实例') }}</strong>
    </div>
    <BkTab
      v-if="activeGroup !== null"
      v-model:active="activePanel"
      type="unborder-card">
      <BkTabPanel
        v-for="item in panels"
        :key="item.name"
        :label="item.label"
        :name="item.name" />
    </BkTab>
    <BkLoading :loading="loading">
      <InstanceList
        v-if="activePanel === 'instance'"
        :data="activeGroup" />
      <RuleList
        v-else
        :data="activeGroup" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getDumperConfigDetail, listDumperConfig } from '@services/source/dumper';

  import InstanceList from './components/instance-list/Index.vue';
  import RuleList from './components/RuleList.vue';

  interface Props {
    data: DumperConfig | null;
  }

  type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const activePanel = ref('instance');
  const activeGroup = ref<DumperConfig | null>(null);

  const panels = [
    { name: 'instance', label: t('实例列表') },
    { name: 'rule', label: t('订阅规则') },
  ];

  const { loading, run: runGetDumperConfigDetail } = useRequest(getDumperConfigDetail, {
    manual: true,
    onSuccess: (res) => {
      activeGroup.value = res;
    },
  });

  watch(
    () => props.data,
    () => {
      if (props.data?.id) {
        runGetDumperConfigDetail({ id: props.data.id });
        return;
      }
      activePanel.value = 'instance';
      activeGroup.value = null;
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .dumper-render-list {
    height: 100%;
    padding: 24px;
    background-color: white;

    :deep(.bk-tab-content) {
      display: none;
    }

    tr {
      &:hover {
        .db-icon-copy {
          display: inline-block;
        }
      }
    }

    .instances-view-header {
      display: flex;
      height: 20px;
      margin-bottom: 16px;
      color: @title-color;
      align-items: center;

      .instances-view-header-icon {
        font-size: 18px;
        color: @gray-color;
      }
    }

    .instances-view-operations {
      display: flex;
      align-items: center;
      padding: 16px 0;

      .instances-view-operations-right {
        flex: 1;
        display: flex;
        justify-content: flex-end;
      }

      .bk-button {
        margin-right: 8px;
      }

      .dropdown-button {
        .dropdown-button-icon {
          margin-left: 6px;
          transition: all 0.2s;
        }

        &.active:not(.is-disabled) {
          .dropdown-button-icon {
            transform: rotate(180deg);
          }
        }
      }
    }

    .instance-box {
      display: flex;
      align-items: flex-start;
      padding: 8px 0;
      overflow: hidden;

      .instance-name {
        line-height: 20px;
      }

      .cluster-tags {
        display: flex;
        margin-left: 4px;
        align-items: center;
        flex-wrap: wrap;
      }

      .cluster-tag {
        margin: 2px;
        flex-shrink: 0;
      }

      .db-icon-copy {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    .is-offline {
      a {
        color: @gray-color;
      }

      .cell {
        color: @disable-color;
      }
    }
  }

  .bk-dropdown-item {
    &.is-disabled {
      color: @disable-color;
      cursor: not-allowed;
    }
  }
</style>
