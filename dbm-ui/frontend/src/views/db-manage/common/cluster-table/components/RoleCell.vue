<template>
  <div class="cluster-table-role-instances-list-box">
    <template
      v-for="rowItem in displayRows"
      :key="rowItem.type === 'shard' ? `shard#${rowItem.segRange}` : `${rowItem.node.ip}:${rowItem.node.port}`">
      <div
        v-if="rowItem.type === 'shard'"
        class="shard-group-title">
        {{ rowItem.segRange }} ({{ rowItem.count }})
      </div>
      <div
        v-else
        :class="{
          'is-unavailable': rowItem.node.status === 'unavailable',
          'is-shard-child': hasSegRangeGroup,
        }">
        <TextOverflowLayout>
          <div class="pr-4">
            <TextHighlight
              ref="hightlightRefs"
              high-light-color="#F59500"
              :keyword="searchKeyword"
              :text="`${rowItem.node.ip}:${rowItem.node.port}`">
              <slot
                name="default"
                v-bind="{
                  data: rowItem.node as any,
                }" />
            </TextHighlight>
          </div>
          <template #append>
            <BkTag
              v-if="rowItem.node.status === 'unavailable'"
              size="small">
              {{ t('不可用') }}
            </BkTag>
            <slot
              v-bind="{
                data: rowItem.node as any,
              }"
              name="nodeTag" />
            <span v-if="rowItem.showCopy">
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
    </template>
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

  type DisplayRow =
    | {
        count: number;
        segRange: string;
        type: 'shard';
      }
    | {
        node: ClusterListNode;
        showCopy: boolean;
        type: 'node';
      };

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

  const visibleNodes = computed(() => props.data.slice(0, renderInstanceCount));

  const hasSegRangeGroup = computed(() => visibleNodes.value.some((item) => Boolean(item.seg_range)));

  const displayRows = computed((): DisplayRow[] => {
    const nodes = visibleNodes.value;
    if (!hasSegRangeGroup.value) {
      return nodes.map((node, index) => ({ type: 'node' as const, node, showCopy: index === 0 }));
    }

    const rows: DisplayRow[] = [];
    let index = 0;
    let firstNode = true;
    while (index < nodes.length) {
      const segRange = nodes[index].seg_range || '';
      let end = index + 1;
      while (end < nodes.length && (nodes[end].seg_range || '') === segRange) {
        end += 1;
      }
      if (segRange) {
        rows.push({ type: 'shard', segRange, count: end - index });
      }
      for (let i = index; i < end; i += 1) {
        rows.push({ type: 'node', node: nodes[i], showCopy: firstNode });
        firstNode = false;
      }
      index = end;
    }
    return rows;
  });

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

    .shard-group-title {
      margin-top: 4px;
      margin-bottom: 2px;
      font-weight: 500;
      color: #63656e;
    }

    .is-shard-child {
      padding-left: 8px;
    }
  }
</style>
