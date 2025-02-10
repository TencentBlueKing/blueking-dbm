<template>
  <BaseRoleColumn
    v-bind="props"
    :min-width="280">
    <template #default="{ data }">
      {{ data.ip }}:{{ data.port }}
      <template v-if="data.seg_range">({{ data.seg_range }})</template>
    </template>
    <template #instanceListTitle="{ data }">
      <I18nT keypath="c实例预览r_n">
        <span>{{ data.master_domain }}</span>
        <span>Master/Slave</span>
        <span>{{ data.redis_master.length }}</span>
      </I18nT>
    </template>
    <template #instanceList="{ clusterData }: { clusterData: RedisModel }">
      <BkTable :data="clusterData.redis_master">
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
                  <BkDropdownItem @click="handleCopy(clusterData.redis_master, 'ip')">
                    {{ t('复制 IP') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopy(clusterData.redis_master, 'instance')">
                    {{ t('复制实例') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </template>
          <template #default="{ data }: { data: RedisModel['redis_master'][number] }">
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
                  <BkDropdownItem @click="handleCopy(clusterData.redis_slave, 'ip')">
                    {{ t('复制 IP') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopy(clusterData.redis_slave, 'instance')">
                    {{ t('复制实例') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </template>
          <template #default="{ rowIndex }: { rowIndex: number }">
            {{ clusterData.redis_slave[rowIndex]?.instance || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('分片')">
          <template #default="{ data }: { data: RedisModel['redis_master'][number] }">
            {{ data.seg_range || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
    </template>
  </BaseRoleColumn>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { ClusterTypes } from '@common/const';

  import BaseRoleColumn, {
    type Props,
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  const props = defineProps<Props<ClusterTypes.REDIS, 'redis_master' | 'redis_slave'>>();

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
