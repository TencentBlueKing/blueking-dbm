<template>
  <BkTableColumn
    field="model"
    :label="label"
    :min-width="400">
    <template #default="{ data }: { data: ResourceSpecModel }">
      <BkPopover
        disable-outside-click
        :max-width="600"
        placement="top"
        :popover-delay="[300, 0]"
        theme="light">
        <template #content>
          <div class="resource-machine-info-tips">
            <template v-if="data.cpu.min > 0 && data.device_class.length === 0">
              <strong>CPU: </strong>
              <div class="resource-machine-info-values mb-10">
                <BkTag> {{ `${data.cpu.min} ~ ${data.cpu.max}` }} {{ t('核') }} </BkTag>
              </div>
              <strong>{{ t('内存') }}: </strong>
              <div class="resource-machine-info-values mb-10">
                <BkTag>{{ `${data.mem.min} ~ ${data.mem.max}` }} G</BkTag>
              </div>
            </template>
            <template v-if="data.device_class.length > 0">
              <strong>{{ t('机型') }}: </strong>
              <div class="resource-machine-info-values mb-10">
                <BkTag
                  v-for="(item, index) in data.device_class"
                  :key="index"
                  class="mb-4">
                  {{ item }}
                </BkTag>
              </div>
            </template>
            <strong>{{ t('磁盘') }}: </strong>
            <div class="resource-machine-info-values">
              <template v-if="data.storage_spec.length > 0">
                <p
                  v-for="(item, index) in data.storage_spec"
                  :key="index">
                  <BkTag class="mb-4">
                    {{
                      `(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${deviceClassDisplayMap[item.type as DeviceClass]})`
                    }}
                  </BkTag>
                </p>
              </template>
              <span v-else>--</span>
            </div>
          </div>
        </template>
        <div class="machine-info text-overflow">
          <template v-if="data.cpu.min > 0 && data.device_class.length === 0">
            <BkTag class="machine-info-cpu"> CPU = {{ `${data.cpu.min} ~ ${data.cpu.max}` }} {{ t('核') }} </BkTag>
            <BkTag
              class="machine-info-condition"
              theme="info">
              AND
            </BkTag>
            <BkTag class="machine-info-mem"> {{ t('内存') }} = {{ `${data.mem.min} ~ ${data.mem.max}` }} G </BkTag>
            <BkTag
              class="machine-info-condition"
              theme="info">
              AND
            </BkTag>
          </template>
          <template v-if="data.device_class.length > 0">
            <BkTag class="machine-info-device"> {{ t('机型') }} = {{ data.device_class.join(',') }} </BkTag>
            <BkTag
              class="machine-info-condition"
              theme="info">
              AND
            </BkTag>
          </template>
          <BkTag class="machine-info-storage">
            {{ t('磁盘') }} =
            <template v-if="data.storage_spec.length > 0">
              <span
                v-for="(item, index) in data.storage_spec"
                :key="index">
                {{
                  `(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${deviceClassDisplayMap[item.type as DeviceClass]})`
                }}
              </span>
            </template>
            <span v-else>--</span>
          </BkTag>
        </div>
      </BkPopover>
    </template>
  </BkTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

  interface Props {
    label: string;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less">
  .resource-machine-info-tips {
    min-width: 280px;
    padding: 9px 0 0;
    color: #63656e;

    .resource-machine-info-values {
      margin: 6px 0;
    }
  }
</style>
