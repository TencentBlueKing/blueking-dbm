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
                @click="(event: Event) => handleCopyIp(groupItem.data, event)">
                <DbIcon type="copy" />
              </BkButton>
            </div>
          </template>
          <template #content>
            <BkTable
              :data="groupItem.data"
              :row-config="{
                useKey: true,
                keyField: 'ip',
              }">
              <BkTableColumn
                field="ip"
                fixed="left"
                label="IP"
                :width="200">
                <template #default="{ data }: { data: IResouce & { tag: string } }">
                  {{ data.ip }}
                  <BkTag v-if="data.tag">{{ data.tag }}</BkTag>
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="city"
                :label="t('地域')"
                :min-width="100">
                <template #default="{ data }: { data: IResouce }">
                  {{ data.city || '--' }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="sub_zone"
                :label="t('园区')"
                :min-width="100">
                <template #default="{ data }: { data: IResouce }">
                  {{ data.sub_zone || '--' }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="rack_id"
                :label="t('机架')"
                :min-width="100">
                <template #default="{ data }: { data: IResouce }">
                  {{ data.rack_id || '--' }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="os_type"
                :label="t('操作系统名称')"
                :min-width="180">
                <template #default="{ data }: { data: IResouce }">
                  {{ data.os_type || '--' }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="device_class"
                :label="t('机型')"
                :min-width="100">
                <template #default="{ data }: { data: IResouce }">
                  {{ data.device_class || '--' }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="bk_cpu"
                :label="t('CPU_核_')"
                :min-width="100" />
              <BkTableColumn
                field="bk_mem"
                :label="t('内存M')"
                :min-width="100" />
              <BkTableColumn
                field="bk_disk"
                :label="t('磁盘G')"
                :min-width="100" />
            </BkTable>
          </template>
        </BkCollapsePanel>
      </template>
    </BkCollapse>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { execCopy } from '@utils';

  interface IResouce {
    bk_cloud_id: number;
    bk_cpu: number;
    bk_disk: number;
    bk_mem: number;
    city: string;
    device_class: string;
    ip: string;
    os_name: string;
    os_type: string;
    rack_id: string;
    sub_zone: string;
  }

  interface Props {
    ticketDetail: TicketModel<{
      nodes: Record<string, IResouce[] | Record<string, IResouce>[]>;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const collapseExpandIndex = ref<number[]>([]);

  const renderGroupData = shallowRef<{ data: IResouce[]; groupName: string }[]>([]);

  watchEffect(() => {
    const nodes = props.ticketDetail.details.nodes;
    renderGroupData.value = Object.keys(nodes).map((nodeName) => {
      const nodeDataList = nodes[nodeName];
      if (nodeDataList[0].ip) {
        return {
          data: nodes[nodeName] as IResouce[],
          groupName: nodeName,
        };
      }
      return {
        data: (nodeDataList as Record<string, IResouce>[]).reduce(
          (result, item) => {
            Object.keys(item).forEach((itemKey) => {
              result.push({
                tag: itemKey,
                ...item[itemKey],
              });
            });
            return result;
          },
          [] as ({ tag: string } & IResouce)[],
        ),
        groupName: nodeName,
      };
    });
    collapseExpandIndex.value = renderGroupData.value.map((item, index) => index);
  });

  const handleCopyIp = (data: IResouce[], event: Event) => {
    event.stopPropagation();
    event.stopImmediatePropagation();
    execCopy(data.map((item) => item.ip).join('\n'), t('复制成功，共n条', { n: data.length }));
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
