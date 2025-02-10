<template>
  <BaseRoleColumn
    v-bind="props"
    :min-width="240">
    <template #default="{ data }"> {{ data.ip }}:{{ data.port }}(%_{{ data.shard_id }}) </template>
    <template #instanceListTitle="{ data }">
      <I18nT keypath="c实例预览r_n">
        <span>{{ data.master_domain }}</span>
        <span>RemoteDB/DR</span>
        <span>{{ data.remote_db.length }}</span>
      </I18nT>
    </template>
    <template #instanceList="{ clusterData }: { clusterData: TendbClusterModel }">
      <BkTable :data="clusterData.remote_db">
        <BkTableColumn label="RemoteDB">
          <template #header>
            <span>RemoteDB</span>
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
                  <BkDropdownItem @click="handleCopy(clusterData.remote_db, 'ip')">
                    {{ t('复制 IP') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopy(clusterData.remote_db, 'instance')">
                    {{ t('复制实例') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </template>
          <template #default="{ data }: { data: TendbClusterModel['remote_db'][number] }">
            {{ data.instance }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="RemoteDR">
          <template #header>
            <span>RemoteDR</span>
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
                  <BkDropdownItem @click="handleCopy(clusterData.remote_dr, 'ip')">
                    {{ t('复制 IP') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopy(clusterData.remote_dr, 'instance')">
                    {{ t('复制实例') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </template>
          <template #default="{ rowIndex }: { rowIndex: number }">
            {{ clusterData.remote_dr[rowIndex]?.instance || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="Shard_id">
          <template #default="{ data }: { data: TendbClusterModel['remote_db'][number] }">
            {{ data.shard_id }}
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
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  const props = defineProps<Props<ClusterTypes.TENDBCLUSTER, 'remote_db' | 'remote_dr'>>();

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
