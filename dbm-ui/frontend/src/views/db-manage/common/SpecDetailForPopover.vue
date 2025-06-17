<template>
  <div class="spec-detail-for-popover">
    <div class="title">
      {{ data.spec_name }}
    </div>
    <table class="info-box">
      <tbody>
        <tr>
          <td>CPU:</td>
          <td>
            <span>{{ data.cpu.min }} ~ {{ data.cpu.max }} {{ t('核') }}</span>
          </td>
        </tr>
        <tr>
          <td>{{ t('内存') }}:</td>
          <td>
            <span>{{ data.mem.min }} ~ {{ data.mem.max }} G</span>
          </td>
        </tr>
        <tr>
          <td>{{ t('磁盘') }}:</td>
          <td>
            <BkTable
              :data="data.storage_spec"
              :max-height="200"
              style="width: 420px">
              <BkTableColumn
                field="mount_point"
                :label="t('挂载点')" />
              <BkTableColumn
                field="size"
                :label="t('最小容量G')" />
              <BkTableColumn :label="t('磁盘类型')">
                <template #default="{ data: rowData }: { data: ResourceSpecModel['storage_spec'][number] }">
                  {{ deviceClassDisplayMap[rowData.type as DeviceClass] }}
                </template>
              </BkTableColumn>
            </BkTable>
          </td>
        </tr>
        <tr>
          <td>{{ t('每台主机实例数量') }}:</td>
          <td>
            <span>{{ data.instance_num }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

  interface Props {
    data: ResourceSpecModel;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .spec-detail-for-popover {
    padding: 6px 4px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .title {
      font-weight: bold;
    }

    .info-box {
      & > tr > td {
        line-height: 32px;
        vertical-align: top;

        &:first-child {
          width: 118px;
          padding-right: 8px;
          text-align: right;
        }

        &:last-child {
          color: #313238;
        }
      }
    }
  }
</style>
