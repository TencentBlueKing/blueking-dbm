<template>
  <div class="dbm-cluster-role-status">
    <BkPopover
      :max-width="500"
      placement="top"
      :popover-delay="[300, 100]"
      theme="light">
      <ClusterStatus :data="data.status" />
      <template #content>
        <div class="dbm-cluster-role-status-panel">
          <table>
            <tr
              v-for="roleName in Object.keys(data.roleFailedInstanceInfo)"
              :key="roleName">
              <td style="padding-right: 4px; vertical-align: top">
                <ClusterStatus
                  :data="data.roleFailedInstanceInfo[roleName].length > 0 ? 'abnormal' : 'normal'"
                  :show-text="false"
                  style="display: inline-flex; margin-right: 4px" />
                <span>{{ roleName }}:</span>
              </td>
              <td style="vertical-align: top">
                <div v-if="data.roleFailedInstanceInfo[roleName].length > 0">
                  <div>
                    <I18nT keypath="n个实例不可用">
                      <span style="font-weight: bold">{{ data.roleFailedInstanceInfo[roleName].length }}</span>
                    </I18nT>
                  </div>
                  <div>
                    <span>{{
                      data.roleFailedInstanceInfo[roleName]
                        .slice(0, 3)
                        .map((item) => item.ip)
                        .join(', ')
                    }}</span>
                    <span v-if="data.roleFailedInstanceInfo[roleName].length > 3"> ... </span>
                    <DbIcon
                      class="copy-btn"
                      type="copy"
                      @click="handleCopy(roleName)" />
                  </div>
                </div>
                <div v-else>{{ t('正常') }}</div>
              </td>
            </tr>
          </table>
        </div>
      </template>
    </BkPopover>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ClusterListNode } from '@services/types';

  import ClusterStatus from '@components/cluster-status/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    data: {
      status: string;
      roleFailedInstanceInfo: Record<any, ClusterListNode[]>;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const handleCopy = (role: keyof Props['data']['roleFailedInstanceInfo']) => {
    const ipList = props.data.roleFailedInstanceInfo[role].map((item) => item.ip);
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
  };
</script>
<style lang="less">
  .dbm-cluster-role-status-panel {
    line-height: 24px;
    color: #63656e;

    .copy-btn {
      cursor: pointer;

      &:hover {
        color: #3a84ff;
      }
    }
  }
</style>
