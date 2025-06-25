<template>
  <div class="cluster-table-role-instances-list-box">
    <div
      v-for="(instanceItem, index) in data.slice(0, renderInstanceCount)"
      :key="`${instanceItem.ip}:${instanceItem.port}`"
      :class="{
        'is-unavailable': instanceItem.status === 'unavailable',
      }">
      <TextOverflowLayout>
        <div class="pr-4">
          <TextHighlight
            ref="hightlightRefs"
            high-light-color="#F59500"
            :keyword="searchKeyword"
            :text="`${instanceItem.ip}:${instanceItem.port}`">
            <slot
              name="default"
              v-bind="{
                data: instanceItem as any,
              }" />
          </TextHighlight>
        </div>
        <template #append>
          <BkTag
            v-if="instanceItem.status === 'unavailable'"
            size="small">
            {{ t('不可用') }}
          </BkTag>
          <slot
            v-bind="{
              data: instanceItem as any,
            }"
            name="nodeTag" />
          <span v-if="index === 0">
            <PopoverCopy>
              <div @click="handleCopyIp">
                {{ t('复制IP') }}
              </div>
              <div @click="handleCopyInstance">
                {{ t('复制实例') }}
              </div>
            </PopoverCopy>
          </span>
        </template>
      </TextOverflowLayout>
    </div>
    <template v-if="data.length < 1"> -- </template>
    <template v-if="data.length > renderInstanceCount">
      <span
        style="color: #3a84ff; cursor: pointer"
        @click="handleShowMore">
        <I18nT
          v-if="hightlightCount > 0"
          keypath="_查询到_个_">
          <DbIcon
            style="display: inline !important; margin-right: 2px; color: #f59500"
            type="hongqi" />
          {{ hightlightCount }}
        </I18nT>
        <I18nT
          v-else
          keypath="共n个_">
          {{ data.length }}
        </I18nT>
        {{ t('查看更多') }}
      </span>
    </template>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import type { ClusterListNode } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { batchSplitRegex } from '@common/regex';

  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, makeMap, messageWarn } from '@utils';

  interface Props {
    data: ClusterListNode[];
  }

  interface Slot {
    default: (params: { data: ClusterListNode }) => VNode;
    nodeTag: (params: { data: ClusterListNode }) => VNode;
  }

  export type Emits = (e: 'go-detail', event: MouseEvent) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  defineSlots<Slot>();

  const { t } = useI18n();

  const renderInstanceCount = 6;
  const route = useRoute();
  const { removeSearchParam } = useUrlSearch();

  const searchKeyword = ref('');

  const hightlightRefs = ref<InstanceType<typeof TextHighlight>[]>();

  const hightlightCount = computed(() => {
    if (!searchKeyword.value) {
      return 0;
    }

    const keywordMap = makeMap(_.filter(searchKeyword.value.split(batchSplitRegex), (item) => Boolean(_.trim(item))));
    return _.filter(props.data, (item) => keywordMap[item.ip] || keywordMap[item.instance]).length;
  });

  watch(
    route,
    () => {
      searchKeyword.value = (route.query.instance as string) || '';
    },
    {
      immediate: true,
    },
  );

  const handleCopyIp = () => {
    const ipList = [...new Set(props.data.map((item) => item.ip))];
    if (ipList.length === 0) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleCopyInstance = () => {
    const instanceList = props.data.map((item) => `${item.ip}:${item.port}`);
    if (instanceList.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(
      instanceList.join('\n'),
      t('复制成功，共n条', {
        n: instanceList.length,
      }),
    );
  };

  const handleShowMore = (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    removeSearchParam('__detail_panel__');
    emits('go-detail', event);
  };
</script>
<style lang="less">
  .cluster-table-role-instances-list-box {
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
</style>
