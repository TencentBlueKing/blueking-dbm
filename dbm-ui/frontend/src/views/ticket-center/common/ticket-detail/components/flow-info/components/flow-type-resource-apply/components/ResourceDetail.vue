<template>
  <div
    v-if="isShow"
    class="flow-resource-detail">
    <BkCollapse>
      <BkCollapsePanel name="detail">
        <template #header>
          <div class="box-header">
            <DbIcon type="right-shape" />
            <div class="ml-8">{{ t('资源明细') }}</div>
          </div>
        </template>
        <template #content>
          <div class="resoure-wrapper">
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
                      <span>{{ groupItem.groupName }}</span>
                      <span>({{ groupItem.count }})</span>
                      <BkButton
                        class="ml-4"
                        text
                        theme="primary"
                        @click="(event: Event) => handleCopyIp(groupItem, event)">
                        <DbIcon type="copy" />
                      </BkButton>
                      <DbIcon
                        class="resource-colllapse-flag"
                        type="right-big" />
                    </div>
                  </template>
                  <template #content>
                    <div class="host-wrapper">
                      <ResourceDetailHostTable
                        v-if="groupItem.data.length"
                        :data="groupItem.data" />
                      <template v-if="groupItem.list.length">
                        <ResourceDetailHostTable
                          v-for="(item, itemIndex) in groupItem.list"
                          :key="itemIndex"
                          :data="item" />
                      </template>
                    </div>
                  </template>
                </BkCollapsePanel>
              </template>
            </BkCollapse>
          </div>
        </template>
      </BkCollapsePanel>
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

  const renderGroupData = shallowRef<
    {
      count: number;
      data: IResouce[];
      groupName: string;
      list: ({ tag: string } & IResouce)[][];
    }[]
  >([]);

  const isShow = computed(() => Object.keys(props.ticketDetail.details.nodes || {}).length > 0);

  watchEffect(() => {
    const nodes = props.ticketDetail.details.nodes;
    renderGroupData.value = Object.keys(nodes).map((nodeName) => {
      const nodeDataList = nodes[nodeName];
      const groupName = _.trim(nodeName.replace(/\d/g, '').split(/_+/).join('_'), '_');
      if (nodeDataList[0].ip) {
        return {
          count: nodes[nodeName].length,
          data: nodes[nodeName] as IResouce[],
          groupName,
          list: [],
        };
      }
      const multDataList = (nodeDataList as Record<string, IResouce>[]).map((item) => {
        return Object.keys(item).map((nodeKey) => ({
          tag: nodeKey,
          ...item[nodeKey],
        }));
      });
      return {
        count: _.flatten(multDataList).length,
        data: [],
        groupName,
        list: multDataList,
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
    position: relative;
    z-index: 0;
    display: block;
    background: #f5f7fa;

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

    .box-header {
      display: flex;
      padding: 12px 9px;
      font-weight: bold;
      color: #4d4f56;
      align-items: center;
      cursor: pointer;
    }

    .resoure-wrapper {
      .bk-collapse-item-active {
        .resource-header {
          .resource-colllapse-flag {
            transform: rotate(90deg);
          }
        }
      }

      .bk-collapse-item {
        margin-bottom: 18px;
      }
    }

    .resource-header {
      display: flex;
      height: 28px;
      padding: 0 12px;
      margin: 0 16px 0 32px;
      font-weight: 500;
      color: #313238;
      cursor: pointer;
      background: #f0f1f5;
      user-select: none;
      align-items: center;
      align-content: center;

      .resource-colllapse-flag {
        margin-left: auto;
        font-size: 18px;
        color: #979ba5;
      }
    }

    .host-wrapper {
      padding: 0 16px 0 32px;
    }
  }
</style>
