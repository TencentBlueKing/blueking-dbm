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
  <div class="cluster-list-role-instances-list-box">
    <div
      v-for="(inst, index) in data"
      :key="`${inst.ip}:${inst.port}`"
      :class="{ 'is-unavailable': inst.status === 'unavailable' }">
      <TextOverflowLayout>
        <span
          class="pr-4"
          :style="{
            color:
              highlightIps.includes(inst.ip) || highlightIps.includes(`${inst.ip}:${inst.port}`)
                ? 'rgb(255 130 4)'
                : '',
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
          </template>
        </template>
      </TextOverflowLayout>
    </div>
    <template v-if="data.length < 1"> -- </template>
    <template v-if="hasMore">
      <BkButton
        text
        theme="primary"
        @click="handleShowMore">
        {{ t('查看更多') }}
      </BkButton>
    </template>
  </div>
  <div style="display: none">
    <div ref="popRef">
      <BkButton
        class="cluster-role-instance-copy-btn"
        text
        theme="primary"
        @click="handleCopyIps">
        {{ t('复制IP') }}
      </BkButton>
      <span class="cluster-role-instance-copy-btn-split" />
      <BkButton
        class="cluster-role-instance-copy-btn"
        text
        theme="primary"
        @click="handleCopyInstances">
        {{ t('复制实例') }}
      </BkButton>
    </div>
  </div>
  <RenderInstanceList
    v-model:is-show="isShowMore"
    :data="data"
    :role="role"
    :title="title" />
</template>
<script lang="ts">
  type IData = {
    ip: string;
    port: number;
    status: string;
    shard_id?: string;
  };
</script>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  import RenderInstanceList from './Instacelist.vue';

  interface Props {
    title: string;
    role: string;
    data: IData[];
    highlightIps?: string[];
  }

  const props = withDefaults(defineProps<Props>(), {
    highlightIps: () => [],
    tagKeyConfig: () => [],
  });

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();

  let tippyIns: Instance;

  const renderCount = 10;

  const copyRootRef = ref();
  const popRef = ref();
  const isCopyIconClicked = ref(false);
  const isShowMore = ref(false);
  const hasMore = computed(() => props.data.length > renderCount);

  const handleShowMore = () => {
    isShowMore.value = true;
  };

  const handleCopyIps = () => {
    const { data } = props;
    const ipList = [...new Set(data.map((item) => item.ip))];
    if (ipList.length === 0) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(
      ipList.join('\n'),
      t('成功复制n个', {
        n: ipList.length,
      }),
    );
  };

  const handleCopyInstances = () => {
    const instanceList = props.data.map((item) => `${item.ip}:${item.port}`);
    execCopy(
      instanceList.join('\n'),
      t('成功复制n个', {
        n: instanceList.length,
      }),
    );
  };

  onMounted(() => {
    nextTick(() => {
      if (copyRootRef.value) {
        tippyIns = tippy(copyRootRef.value[0].$el as SingleTarget, {
          content: popRef.value,
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
<style lang="less">
  .cluster-list-role-instances-list-box {
    padding: 6px 0;

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
  }

  .cluster-role-instance-copy-btn {
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

  .cluster-role-instance-copy-btn-split {
    display: inline-block;
    width: 1px;
    height: 18px;
    margin: 0 4px;
    vertical-align: middle;
    background-color: #f0f1f5;
  }
</style>
