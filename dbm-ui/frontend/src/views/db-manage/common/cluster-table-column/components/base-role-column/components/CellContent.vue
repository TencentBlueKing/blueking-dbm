<template>
  <div>
    <div
      class="cluster-list-role-instances-list-box"
      @mouseenter="handleToolsShow">
      <div
        v-for="(instanceItem, index) in renderData"
        :key="`${instanceItem.ip}:${instanceItem.port}`"
        :class="{ 'is-unavailable': instanceItem.status === 'unavailable' }">
        <TextOverflowLayout>
          <div
            class="pr-4"
            :style="{
              color:
                hightlightKey?.includes(instanceItem.ip) ||
                hightlightKey?.includes(`${instanceItem.ip}:${instanceItem.port}`)
                  ? 'rgb(255 130 4)'
                  : '',
            }">
            <slot
              name="default"
              v-bind="{
                data: instanceItem,
              }">
              {{ instanceItem.ip }}:{{ instanceItem.port }}
            </slot>
          </div>
          <template #append>
            <BkTag
              v-if="instanceItem.status === 'unavailable'"
              size="small">
              {{ t('不可用') }}
            </BkTag>
            <slot
              v-if="data.length > 1"
              v-bind="{
                data: instanceItem,
              }"
              name="nodeTag" />
            <span v-if="index === 0 && isToolsShow">
              <PopoverCopy>
                <div @click="handleCopyIps">{{ t('复制IP') }}</div>
                <div @click="handleCopyInstances">{{ t('复制实例') }}</div>
              </PopoverCopy>
            </span>
          </template>
        </TextOverflowLayout>
      </div>
      <template v-if="data.length < 1"> -- </template>
      <template v-if="isShowMore">
        <span
          style="color: #3a84ff; cursor: pointer"
          @click="handleShowMore">
          <I18nT keypath="共n个">
            {{ data.length }}
          </I18nT>
          ,
          {{ t('查看更多') }}
        </span>
      </template>
    </div>
    <BkDialog
      v-if="isToolsShow && isShowMore"
      v-model:is-show="isShowInstanceDetail"
      render-directive="if"
      :title="title"
      :width="1100">
      <template #header>
        <slot name="instanceListTitle">
          {{
            t('【inst】实例预览', {
              inst: clusterData.masterDomain,
              title: label,
            })
          }}
        </slot>
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
  import { useI18n } from 'vue-i18n';

  import type { ClusterListNode } from '@services/types';

  import PopoverCopy from '@components/popover-copy/Index.vue';
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
    default: (params: { data: { ip: string; port: number; status: string } }) => VNode;
    nodeTag: (params: { data: { ip: string; port: number; status: string } }) => VNode;
    instanceListTitle: () => VNode;
    instanceList: () => VNode;
  }>();

  const { t } = useI18n();

  const renderInstanceCount = 6;

  const isToolsShow = ref(false);
  const isShowInstanceDetail = ref(false);
  const isShowMore = computed(() => props.data.length > renderInstanceCount);

  const renderData = computed(() => props.data.slice(0, renderInstanceCount));

  const handleToolsShow = () => {
    setTimeout(() => {
      isToolsShow.value = true;
    }, 1000);
  };

  const handleCopyIps = () => {
    const ipList = [...new Set(props.data.map((item) => item.ip))];
    if (ipList.length === 0) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
  };

  const handleCopyInstances = () => {
    const instanceList = props.data.map((item) => `${item.ip}:${item.port}`);
    execCopy(instanceList.join('\n'), t('复制成功，共n条', { n: instanceList.length }));
  };

  const handleShowMore = () => {
    isShowInstanceDetail.value = true;
  };

  const handleClose = () => {
    isShowInstanceDetail.value = false;
  };
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
