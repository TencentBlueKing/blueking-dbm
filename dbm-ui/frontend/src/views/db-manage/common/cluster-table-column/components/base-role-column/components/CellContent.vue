<template>
  <div>
    <div class="cluster-list-role-instances-list-box">
      <div
        v-for="(instanceItem, index) in data"
        :key="`${instanceItem.ip}:${instanceItem.port}`"
        :class="{ 'is-unavailable': instanceItem.status === 'unavailable' }">
        <TextOverflowLayout>
          <span
            class="pr-4"
            :style="{
              color:
                hightlightKey?.includes(instanceItem.ip) ||
                hightlightKey?.includes(`${instanceItem.ip}:${instanceItem.port}`)
                  ? 'rgb(255 130 4)'
                  : '',
            }">
            {{ instanceItem.ip }}:{{ instanceItem.port }}
          </span>
          <template #append>
            <BkTag
              v-if="instanceItem.status === 'unavailable'"
              size="small">
              {{ t('不可用') }}
            </BkTag>
            <slot
              v-bind="{ data: instanceItem }"
              name="nodeTag" />
            <span
              v-if="index === 0"
              ref="copyRootRef">
              <DbIcon
                :class="{ 'is-active': isCopyIconClicked }"
                style="display: none"
                type="copy" />
            </span>
          </template>
        </TextOverflowLayout>
      </div>
      <template v-if="data.length < 1"> -- </template>
      <template v-if="data.length > renderInstanceCount">
        <BkButton
          text
          theme="primary"
          @click="handleShowMore">
          <I18nT keypath="共n个">
            {{ data.length }}
          </I18nT>
          ,
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
    <BkDialog
      v-model:is-show="isShowMore"
      render-directive="if"
      :title="title"
      :width="1100">
      <template #header>
        {{
          t('【inst】实例预览', {
            inst: clusterData.masterDomain,
            title: label,
          })
        }}
      </template>
      <slot name="instanceList" />
      <template #footer>
        <BkButton @click="handleClose">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import type { ClusterListNode } from '@services/types';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  interface Props {
    label: string;
    data: ClusterListNode[];
    hightlightKey?: string[];
    title?: string;
    clusterData: {
      masterDomain: string;
    };
  }

  const props = defineProps<Props>();

  defineSlots<{
    nodeTag: (params: { data: { ip: string; port: number; status: string } }) => VNode;
    instanceList: () => VNode;
  }>();

  const { t } = useI18n();

  const renderInstanceCount = 6;

  let tippyIns: Instance;

  const copyRootRef = ref();
  const popRef = ref();
  const isShowMore = ref(false);
  const isCopyIconClicked = ref(false);

  const handleCopyIps = () => {
    const ipList = [...new Set(props.data.map((item) => item.ip))];
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

  const handleShowMore = () => {
    isShowMore.value = true;
  };

  const handleClose = () => {
    isShowMore.value = false;
  };

  onMounted(() => {
    if (copyRootRef.value) {
      tippyIns = tippy(copyRootRef.value[0] as SingleTarget, {
        content: () => popRef.value,
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
    line-height: 24px;
    vertical-align: middle;
    border-radius: 2px;

    * {
      font-size: 12px !important;
    }

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
