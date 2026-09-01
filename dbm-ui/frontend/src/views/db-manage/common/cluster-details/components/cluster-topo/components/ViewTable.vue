<template>
  <div class="cluster-detail-instance-table-view">
    <div
      v-for="groupName in Object.keys(clusterRoleNodeGroup)"
      :key="groupName"
      class="role-item">
      <div class="role-name">
        <span>{{ groupName }} ({{ clusterRoleNodeGroup[groupName].length }})</span>
        <PopoverCopy>
          <div @click="handleCopyHost(clusterRoleNodeGroup[groupName])">{{ t('复制IP') }}</div>
          <div @click="handleCopyInstance(clusterRoleNodeGroup[groupName])">{{ t('复制实例') }}</div>
        </PopoverCopy>
      </div>
      <div class="host-box">
        <ScrollFaker
          ref="scrollContent"
          @scroll="handleContentScroller">
          <div style="padding: 0 12px">
            <template
              v-for="rowItem in roleGroupRowsMap[groupName].rows"
              :key="
                rowItem.type === 'shard'
                  ? `shard#${rowItem.segRange}`
                  : `${rowItem.node.bk_instance_id}#${rowItem.node.instance}`
              ">
              <div
                v-if="rowItem.type === 'shard'"
                class="shard-group-title">
                {{ rowItem.segRange }} ({{ rowItem.count }})
              </div>
              <div
                v-else
                class="node-row"
                :class="{ 'is-shard-child': roleGroupRowsMap[groupName].hasShardGroup }">
                <ClusterInstanceStatus
                  :data="rowItem.node.status"
                  :show-text="false" />
                <div
                  class="ml-4 mr-4"
                  :style="{
                    color: rowItem.node.status === 'unavailable' ? '#c4c6cc' : '',
                  }">
                  <TextHighlight
                    high-light-color="#ff8204"
                    :keyword="serachInstacnce">
                    {{ rowItem.node.displayInstance || rowItem.node.instance }}
                  </TextHighlight>
                </div>
                <MongoNodeTags
                  v-if="isMongoCluster"
                  :data="rowItem.node" />
                <BkTag
                  v-if="!isMongoCluster && rowItem.node.isStandBy"
                  class="cluster-specific-flag ml-4"
                  size="small">
                  Standby
                </BkTag>
                <BkTag
                  v-if="!isMongoCluster && isMasterNode(rowItem.node)"
                  class="cluster-specific-flag ml-4"
                  size="small">
                  {{ masterTagLabel }}
                </BkTag>
                <BkTag
                  v-if="rowItem.node.status === 'unavailable'"
                  class="ml-4"
                  size="small">
                  {{ t('不可用') }}
                </BkTag>
              </div>
            </template>
            <span v-if="clusterRoleNodeGroup[groupName].length < 1">--</span>
          </div>
        </ScrollFaker>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { ClusterListNode } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import PopoverCopy from '@components/popover-copy/Index.vue';
  import ScrollFaker from '@components/scroll-faker/Index.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';

  import MongoNodeTags from '@views/db-manage/mongodb/common/MongoNodeTags.vue';

  import { execCopy, messageWarn } from '@utils';

  const props = defineProps<Props>();

  // 当前主节点标识字段与 Tag 文案，未配置的集群类型沿用 isPrimary 与 Primary 文案
  const clusterTypeWithMasterTagMap: Partial<Record<ClusterTypes, { field: string; label: string }>> = {
    [ClusterTypes.DORIS]: { field: 'is_master', label: 'Master' },
    [ClusterTypes.HDFS]: { field: 'is_active', label: 'Active' },
  };

  type NodeItem = { displayInstance?: string; isPrimary?: boolean; isStandBy?: boolean } & ClusterListNode;

  type GroupRow =
    | {
        count: number;
        segRange: string;
        type: 'shard';
      }
    | {
        node: NodeItem;
        type: 'node';
      };

  interface Props {
    clusterRoleNodeGroup: Record<string, NodeItem[]>;
    clusterType: ClusterTypes;
  }

  const { t } = useI18n();
  const { getSearchParams } = useUrlSearch();

  const serachInstacnce = getSearchParams().instance || '';

  const masterTag = clusterTypeWithMasterTagMap[props.clusterType];
  const masterTagLabel = masterTag?.label ?? 'Primary';

  // Mongo 用自身的角色与副本集状态标签，不再展示 Standby / Primary
  const isMongoCluster = ([ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER] as string[]).includes(
    props.clusterType,
  );

  const isMasterNode = (node: NodeItem) => Boolean(masterTag ? _.get(node, masterTag.field) : node.isPrimary);

  const scrollContentRef = useTemplateRef<InstanceType<typeof ScrollFaker>[]>('scrollContent');

  /** 按分片名聚合：先插分组标题，再列节点（无 seg_range 时保持扁平列表） */
  const getGroupRows = (nodeList: NodeItem[]): GroupRow[] => {
    const rows: GroupRow[] = [];
    for (const [segRange, shardNodes] of Object.entries(_.groupBy(nodeList, (node) => node.seg_range || ''))) {
      if (segRange) {
        rows.push({ count: shardNodes.length, segRange, type: 'shard' });
      }
      rows.push(...shardNodes.map((node) => ({ node, type: 'node' as const })));
    }
    return rows;
  };

  const roleGroupRowsMap = computed(() =>
    Object.fromEntries(
      Object.entries(props.clusterRoleNodeGroup).map(([groupName, nodeList]) => [
        groupName,
        {
          hasShardGroup: nodeList.some((item) => Boolean(item.seg_range)),
          rows: getGroupRows(nodeList),
        },
      ]),
    ),
  );

  const handleCopyHost = (nodeList: ClusterListNode[]) => {
    const ipList = _.uniq(nodeList.map((item) => item.ip));
    if (ipList.length < 1) {
      messageWarn(t('没有可复制 IP'));
      return;
    }

    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleCopyInstance = (nodeList: ClusterListNode[]) => {
    const instanceList = nodeList.map((item) => item.instance);

    if (instanceList.length < 1) {
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

  const handleContentScroller = (event: Event, payload: { left: number; top: number }) => {
    scrollContentRef.value!.forEach((item) => {
      item.scrollTo(payload.left, payload.top);
    });
  };
</script>
<style lang="less">
  .cluster-detail-instance-table-view {
    display: flex;
    height: calc(100% - 92px);
    min-height: 80px;
    font-size: 12px;
    border-bottom: 1px solid #dcdee5;

    .role-item {
      display: flex;
      flex: 1;
      flex-direction: column;

      .role-name {
        display: flex;
        height: 36px;
        padding: 0 12px;
        color: #313238;
        background: #f0f1f5;
        border-bottom: 1px solid #dcdee5;
        flex: 0 0 36px;
        align-items: center;
      }

      .host-box {
        height: calc(100% - 36px);
        padding: 8px 0;
        line-height: 20px;
        color: #4d4f56;
        flex: 1;

        &:hover {
          background: #f5f7fa;

          .cell-copy-btn {
            visibility: visible;
          }
        }

        .cell-copy-btn {
          visibility: hidden;
        }

        .shard-group-title {
          margin-top: 6px;
          margin-bottom: 2px;
          font-weight: 500;
          color: #63656e;
        }

        .node-row {
          display: flex;
          align-items: center;

          &.is-shard-child {
            padding-left: 8px;
          }
        }
      }
    }
  }
</style>
