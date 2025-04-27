<template>
  <div class="flow-resource-detail">
    <BkCollapse
      v-model="collapseExpandIndex"
      header-icon="right-shape"
      use-block-theme>
      <template
        v-for="(groupItem, index) in renderGroupData"
        :key="groupItem.groupName">
        <BkCollapsePanel :name="index">
          <template #header>
            <div class="resource-header">
              <DbIcon
                class="colllapse-flag"
                type="right-shape" />
              <span class="ml-12">{{ groupItem.groupName }}</span>
              <span>({{ groupItem.data.length }})</span>
              <BkButton
                class="ml-4"
                text
                theme="primary"
                @click="(event: Event) => handleCopyIp(groupItem, event)">
                <DbIcon type="copy" />
              </BkButton>
            </div>
          </template>
          <template #content>
            <ResourceDetailHostTable
              v-if="groupItem.data.length"
              :data="groupItem.data" />
            <template v-if="groupItem.list.length">
              <ResourceDetailHostTable
                v-for="(item, itemIndex) in groupItem.list"
                :key="itemIndex"
                :data="item" />
            </template>
          </template>
        </BkCollapsePanel>
      </template>
    </BkCollapse>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { execCopy } from '@utils';

  import ResourceDetailHostTable, { type IResouce } from './ResourceDetailHostTable.vue';

  interface Props {
    ticketDetail: TicketModel<{
      nodes: Record<string, IResouce[] | Record<string, IResouce>[]>;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const collapseExpandIndex = ref<number[]>([]);

  const renderGroupData = shallowRef<{ data: IResouce[]; groupName: string; list: ({ tag: string } & IResouce)[][] }[]>(
    [],
  );

  watchEffect(() => {
    const nodes = props.ticketDetail.details.nodes;
    renderGroupData.value = Object.keys(nodes).map((nodeName) => {
      const nodeDataList = nodes[nodeName];
      const groupName = _.trim(nodeName.replace(/\d/g, '').split(/_+/).join('_'), '_');
      if (nodeDataList[0].ip) {
        return {
          data: nodes[nodeName] as IResouce[],
          groupName,
          list: [],
        };
      }
      return {
        data: [],
        groupName,
        list: (nodeDataList as Record<string, IResouce>[]).map((item) => {
          return Object.keys(item).map((nodeKey) => ({
            tag: nodeKey,
            ...item[nodeKey],
          }));
        }),
      };
    });
    collapseExpandIndex.value = renderGroupData.value.map((item, index) => index);
  });

  const handleCopyIp = (data: UnwrapRef<typeof renderGroupData>[number], event: Event) => {
    event.stopPropagation();
    event.stopImmediatePropagation();
    const copyList = [...data.data, ..._.flatten(data.list)];
    execCopy(copyList.map((item) => item.ip).join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };
</script>
<style lang="less">
  .flow-resource-detail {
    display: block;

    .bk-collapse-header {
      height: 28px;
      line-height: 28px;
    }

    .bk-collapse-content {
      padding: 0;
    }

    .bk-collapse-icon {
      display: none;
    }

    .bk-collapse-item-active {
      .resource-header {
        .colllapse-flag {
          transform: rotate(90deg);
        }
      }
    }

    .resource-header {
      display: flex;
      height: 28px;
      padding: 0 12px;
      font-weight: 500;
      color: #313238;
      cursor: pointer;
      background: #f0f1f5;
      user-select: none;
      align-items: center;
      align-content: center;
    }
  }
</style>
