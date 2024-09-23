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
  <div class="cluster-instances">
    <p
      v-for="(inst, index) in renderData"
      :key="inst.bk_instance_id"
      class="pt-2 pb-2"
      :class="{ 'is-unavailable': inst.status === 'unavailable' }">
      <TextOverflowLayout>
        <span
          class="pr-4"
          :style="{
            color:
              highlightIps.includes(inst.ip) || highlightIps.includes(`${inst.ip}:${inst.port}`)
                ? 'rgb(255 130 4)'
                : '#63656e',
          }">
          <slot :data="inst"> {{ inst.ip }}:{{ inst.port }} </slot>
        </span>
        <template #append>
          <BkTag
            v-if="inst.status === 'unavailable'"
            size="small">
            {{ t('不可用') }}
          </BkTag>
          <slot
            :data="inst"
            name="append" />
          <template v-if="index === 0">
            <DbIcon
              ref="copyRootRef"
              :class="{ 'is-active': isCopyIconClicked }"
              type="copy" />
            <div style="display: none">
              <div ref="popRef">
                <BkButton
                  class="copy-trigger"
                  text
                  theme="primary"
                  @click="handleCopyIps">
                  {{ t('复制IP') }}
                </BkButton>
                <span class="copy-trigger-split" />
                <BkButton
                  class="copy-trigger"
                  text
                  theme="primary"
                  @click="handleCopyInstances">
                  {{ t('复制实例') }}
                </BkButton>
              </div>
            </div>
          </template>
        </template>
      </TextOverflowLayout>
    </p>
    <template v-if="renderData.length < 1"> -- </template>
    <template v-if="hasMore">
      <BkButton
        class="cluster-instances__more"
        text
        theme="primary"
        @click="handleShowMore">
        {{ t('查看更多') }}
      </BkButton>
    </template>
  </div>
  <BkDialog
    v-model:is-show="dialogState.isShow"
    class="cluster-instances-dialog"
    :title="title"
    :width="1100">
    <div class="cluster-instances-content">
      <div class="cluster-instances-content__operations mb-16">
        <BkButton
          class="mr-8"
          @click="handleCopyAbnormal">
          {{ t('复制异常实例') }}
        </BkButton>
        <BkButton
          class="mr-8"
          @click="handleCopyAll">
          {{ t('复制全部实例') }}
        </BkButton>
        <BkInput
          v-model="dialogState.keyword"
          clearable
          :placeholder="t('搜索实例')"
          type="search"
          @clear="fetchInstance"
          @enter="fetchInstance" />
      </div>
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="dataSource"
        fixed-pagination
        :height="440"
        releate-url-query
        @clear-search="handleClearSearch"
        @request-finished="handleRequestFinished" />
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script
  setup
  lang="tsx"
  generic="
    T extends {
      bk_instance_id: number;
      create_at: string;
      instance_address: string;
      ip: string;
      port: number;
      role: string;
      status: string;
    }
  ">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type {
    ListBase,
  } from '@services/types';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    ClusterInstStatusKeys,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageWarn } from '@utils';

  interface Props {
    title: string;
    role: string;
    data: T[];
    clusterId: number;
    dataSource: (params: Record<string, any>) => Promise<ListBase<T[]>>;
    highlightIps?: string[];
  }

  const props = withDefaults(defineProps<Props>(), {
    highlightIps: () => ([]),
    tagKeyConfig: () => ([]),
  });

  const copy = useCopy();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();

  let tippyIns: Instance;

  const copyRootRef = ref();
  const popRef = ref();
  const isCopyIconClicked = ref(false);
  const tableRef = ref();
  const renderData = computed(() => props.data.slice(0, 10));
  const hasMore = computed(() => props.data.length > 10);

  const dialogState = reactive({
    isShow: false,
    keyword: '',
    data: [] as T[],
  });

  const columns = [
    {
      label: t('实例'),
      field: 'instance_address',
    },
    {
      label: t('部署角色'),
      field: 'role',
    },
    {
      label: t('状态'),
      field: 'status',
      render: ({ cell }: { cell: ClusterInstStatus }) => {
        const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('部署时间'),
      field: 'create_at',
    },
  ];

  /**
   * 获取节点列表
   */
  const fetchInstance = () => {
    nextTick(() => {
      tableRef.value.fetchData({
        instance_address: dialogState.keyword,
      }, {
        bk_biz_id: globalBizsStore.currentBizId,
        cluster_id: props.clusterId,
        role: props.role,
      });
    });
  }

  const handleShowMore = () => {
    dialogState.isShow = true;
    fetchInstance();
  }

  const handleClearSearch = () => {
    dialogState.keyword = '';
    fetchInstance();
  }

  const handleRequestFinished = (data: T[]) => {
    dialogState.data = data as UnwrapRef<T[]>;
  }

  /**
   * 复制异常实例
   */
  const handleCopyAbnormal = () => {
    const abnormalInstances = dialogState.data
      .filter(item => item.status !== ClusterInstStatusKeys.RUNNING)
      .map(item => item.instance_address);
    if (abnormalInstances.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(abnormalInstances.join('\n'));
  }

  /**
   * 复制所有实例
   */
  const handleCopyAll = () => {
    const instances = dialogState.data.map(item => item.instance_address);
    if (instances.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(instances.join('\n'));
  }

  const handleCopyIps = () => {
    const { data } = props;
    const ips = [...new Set(data.map(item => item.ip))];
    if (ips.length === 0) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    copy(ips.join('\n'));
  }

  const handleCopyInstances = () => {
    const { data } = props;
    const instances = data.map(item => `${item.ip}:${item.port}`);
    copy(instances.join('\n'));
  }

  const handleClose = () => {
    dialogState.isShow = false;
    dialogState.keyword = '';
    dialogState.data = [];
  }

  onMounted(() => {
    nextTick(() => {
      if (copyRootRef.value) {
        tippyIns = tippy(copyRootRef.value[0].$el as SingleTarget, {
          content: popRef.value[0],
          placement: 'top',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          trigger: 'mouseenter click',
          interactive: true,
          arrow: false,
          allowHTML: true,
          zIndex: 999999,
          hideOnClick: true,
          onShow() {
            isCopyIconClicked.value = true;
          },
          onHide() {
            isCopyIconClicked.value = false;
          },
        });
      }
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .cluster-instances {
    padding: 8px 0;

    .db-icon-copy {
      display: none;
      margin-top: 1px;
      color: @primary-color;
      vertical-align: text-top;
      cursor: pointer;
    }

    .is-active {
      display: inline-block !important;
    }

    .is-unavailable {
      color: #c4c6cc;

      .bk-tag {
        height: 20px;
        padding: 0 4px;
        line-height: 20px;
      }
    }

    &__more {
      display: inline-block;
      margin-top: 2px;
    }

    &-dialog {
      width: 80%;
      max-width: 1600px;
      min-width: 1200px;
    }

    &-content {
      &__operations {
        .flex-center();
      }
    }
  }

  .copy-trigger {
    display: inline-block;
    padding: 0 4px;
    font-size: 12px;
    line-height: 24px;
    vertical-align: middle;
    border-radius: 2px;

    &:hover {
      background-color: #f0f1f5;
    }
  }

  .copy-trigger-split {
    display: inline-block;
    width: 1px;
    height: 18px;
    margin: 0 4px;
    vertical-align: middle;
    background-color: #f0f1f5;
  }
</style>
