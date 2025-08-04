<template>
  <BkPopover
    :offset="18"
    :placement="placement"
    :popover-delay="0"
    theme="light"
    :width="600">
    <slot />
    <template #content>
      <div class="spec-detail-popover-content">
        <span class="spec-name">{{ data?.spec_name || data?.name }}</span>
        <SpecInfo>
          <InfoItem
            v-if="typeof data.availableCount === 'number'"
            :label="t('可用主机数')">
            {{ data.availableCount ?? 0 }}
          </InfoItem>
          <InfoItem
            v-if="data.device_class?.length"
            :label="t('机型')">
            {{ data.device_class.join('，') }}
          </InfoItem>
          <template v-else>
            <InfoItem label="CPU"> ({{ data.cpu.min }} ~ {{ data.cpu.max }}) {{ t('核') }} </InfoItem>
            <InfoItem :label="t('内存')"> ({{ data.mem.min }} ~ {{ data.mem.max }}) G </InfoItem>
          </template>
          <InfoItem :label="t('磁盘')">
            <BkTable :data="data.storage_spec">
              <BkTableColumn
                field="mount_point"
                :label="t('挂载点')" />
              <BkTableColumn
                field="min"
                :label="t('最小容量（G）')">
                <template #default="{ data: rowData }: { data: ResourceSpecModel['storage_spec'][number] }">
                  {{ rowData.size || rowData.min || '--' }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="max"
                :label="t('最大容量（G）')">
                <template #default="{ data: rowData }: { data: ResourceSpecModel['storage_spec'][number] }">
                  {{ rowData.size ? '--' : rowData.max }}
                </template>
              </BkTableColumn>
              <BkTableColumn
                :label="t('磁盘类型')"
                :width="150">
                <template #default="{ data: rowData }: { data: ResourceSpecModel['storage_spec'][number] }">
                  {{ deviceClassDisplayMap[rowData.type as DeviceClass] }}
                </template>
              </BkTableColumn>
            </BkTable>
          </InfoItem>
          <InfoItem
            v-if="data.qps?.max"
            :label="t('单机 QPS')">
            {{ data.qps?.min === data.qps?.max ? `${data.qps?.min}/s` : `${data.qps?.min}/s~${data.qps?.max}/s` }}
          </InfoItem>
          <InfoItem
            v-if="data.instance_num"
            :label="t('每台主机实例数量')">
            {{ data.instance_num }}
          </InfoItem>
        </SpecInfo>
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  import BkPopover from 'bkui-vue/lib/popover';
  import type { VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

  import SpecInfo, { InfoItem } from './components/Index.vue';

  interface Props {
    data: {
      availableCount?: number; // 选择器显示的数量
      cpu: ResourceSpecModel['cpu'];
      device_class?: ResourceSpecModel['device_class'];
      instance_num?: number;
      mem: ResourceSpecModel['mem'];
      name?: string;
      qps?: ResourceSpecModel['qps'];
      spec_name?: string;
      storage_spec: ResourceSpecModel['storage_spec'];
    };
    placement?: ComponentProps<typeof BkPopover>['placement'];
  }

  interface Slots {
    default: () => VNode;
  }

  defineProps<Props>();
  defineSlots<Slots>();

  const { t } = useI18n();
</script>

<style lang="less">
  .spec-detail-popover-content {
    padding: 9px 2px;

    .spec-name {
      font-weight: bolder;
      color: #63656e;
    }
  }
</style>
