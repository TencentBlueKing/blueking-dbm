<template>
  <BaseRoleColumn v-bind="props">
    <template #nodeTag="data">
      <slot
        name="nodeTag"
        v-bind="data" />
    </template>
    <template #instanceListTitle="{ data }">
      <I18nT keypath="c实例预览r_n">
        <span>{{ data.master_domain }}</span>
        <span>Master/Slave</span>
        <span>{{ data.spider_master.length }}</span>
      </I18nT>
    </template>
    <template #instanceList="{ clusterData }: { clusterData: TendbClusterModel }">
      <BkTable :data="clusterData.spider_master">
        <BkTableColumn label="Master">
          <template #header>
            <span>Master</span>
            <BkDropdown>
              <BkButton
                text
                theme="primary">
                <DbIcon
                  class="ml-4"
                  type="copy" />
              </BkButton>
              <template #content>
                <BkDropdownMenu>
                  <BkDropdownItem @click="handleCopy(clusterData.spider_master, 'ip')">
                    {{ t('复制 IP') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopy(clusterData.spider_master, 'instance')">
                    {{ t('复制实例') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </template>
          <template #default="{ data }: { data: TendbClusterModel['spider_master'][number] }">
            {{ data.instance }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="Slave">
          <template #header>
            <span>Slave</span>
            <BkDropdown>
              <BkButton
                text
                theme="primary">
                <DbIcon
                  class="ml-4"
                  type="copy" />
              </BkButton>
              <template #content>
                <BkDropdownMenu>
                  <BkDropdownItem @click="handleCopy(clusterData.spider_slave, 'ip')">
                    {{ t('复制 IP') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopy(clusterData.spider_slave, 'instance')">
                    {{ t('复制实例') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </template>
          <template #default="{ rowIndex }: { rowIndex: number }">
            {{ clusterData.spider_slave[rowIndex]?.instance || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
    </template>
  </BaseRoleColumn>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { ClusterTypes } from '@common/const';

  import BaseRoleColumn, {
    type Props,
    type Slots,
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  const props = defineProps<Props<ClusterTypes.TENDBCLUSTER, 'spider_master' | 'spider_slave'>>();

  defineSlots<Slots<ClusterTypes.TENDBCLUSTER, 'spider_master' | 'spider_slave'>>();
  const { t } = useI18n();

  const handleCopy = (data: { ip: string; instance: string }[], field: 'ip' | 'instance') => {
    const copyData = _.uniq(data.map((item) => item[field]));
    if (copyData.length < 1) {
      messageWarn('数据为空');
      return;
    }
    execCopy(copyData.join('\n'), t('复制成功，共n条', { n: copyData.length }));
  };
</script>
