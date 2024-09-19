<template>
  <div>
    <BkAlert
      closable
      theme="info"
      :title="t('数据迁移：数据同步复制到新集群')" />
    <BkInput
      v-model="searchKeyword"
      :placeholder="t('请输入集群名称')"
      style="width: 500px; margin-top: 16px"
      @change="handelChange" />
    <BkLoading
      :loading="isLoading"
      :pagination="pagination">
      <BkTable
        class="mt-16"
        :data="data">
        <BkTableColumn
          field="source_cluster_domain"
          fixed="left"
          :label="t('源集群')"
          :width="220" />
        <BkTableColumn
          field="target_cluster_domain"
          fixed="left"
          :label="t('目标集群')"
          :width="220" />
        <BkTableColumn
          field="dtsModeText"
          :label="t('迁移类型')"
          :width="180" />
        <BkTableColumn
          field="dtsModeText"
          :label="t('迁移 DB')"
          :width="180">
          <template #default="{ data: rowData }: {data: MigrateRecordModel}">
            <BkTag
              v-for="item in rowData.tagetDb"
              :key="item">
              {{ item }}
            </BkTag>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="dtsModeText"
          :label="t('忽略 DB')"
          :width="180">
          <template #default="{ data: rowData }: {data: MigrateRecordModel}">
            <BkTag
              v-for="item in rowData.ignore_db_list"
              :key="item">
              {{ item }}
            </BkTag>
            <span v-if="rowData.ignore_db_list.length < 1">--</span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="dtsModeText"
          :label="t('关联单据')"
          :width="100">
          <template #default="{ data: rowData }: {data: MigrateRecordModel}">
            <RouterLink
              target="_blank"
              :to="{
                name: 'bizTicketManage',
                query: {
                  id: rowData.ticket_id,
                },
              }">
              {{ rowData.ticket_id }}
            </RouterLink>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="dtsModeText"
          :label="t('状态')"
          :width="180">
          <template #default="{ data: rowData }: {data: MigrateRecordModel}">
            <span
              :class="{ 'rotate-loading': rowData.isRunning }"
              style="display: inline-block; line-height: 0; vertical-align: middle">
              <DbIcon
                svg
                :type="MigrateRecordModel.statusIconMap[rowData.status]" />
            </span>
            <span
              class="ml-4"
              style="vertical-align: middle">
              {{ MigrateRecordModel.statusTextMap[rowData.status] }}
            </span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="createAtDisplay"
          :label="t('创建时间')"
          :width="250" />
        <BkTableColumn
          fixed="right"
          :label="t('操作')"
          :width="150">
          <template #default="{ data: rowData }: {data: MigrateRecordModel}">
            <span
              v-bk-tooltips="{
                content: rowData.forcedTerminationDisableTips,
                disabled: !rowData.forcedTerminationDisableTips,
              }">
              <DbPopconfirm
                :confirm-handler="() => handleForcedTermination(rowData)"
                :content="t('强制终止后将不可恢复_请确认操作')"
                :title="t('确认强制终止')">
                <BkButton
                  :disabled="Boolean(rowData.forcedTerminationDisableTips)"
                  text
                  theme="primary">
                  {{ t('强制终止') }}
                </BkButton>
              </DbPopconfirm>
            </span>
            <span
              v-bk-tooltips="{
                content: rowData.terminateSynceDisableTips,
                disabled: !rowData.terminateSynceDisableTips,
              }">
              <DbPopconfirm
                :confirm-handler="() => handleStopSync(rowData)"
                :content="t('断开同步后将不可恢复_请确认操作')"
                :title="t('确认断开同步')">
                <BkButton
                  class="ml-8"
                  :disabled="Boolean(rowData.terminateSynceDisableTips)"
                  text
                  theme="primary">
                  {{ t('断开同步') }}
                </BkButton>
              </DbPopconfirm>
            </span>
          </template>
        </BkTableColumn>
      </BkTable>
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router'

  import MigrateRecordModel from '@services/model/sqlserver/migrate-record';
  import { forceFailedMigrate, getList, manualTerminateSync } from '@services/source/sqlserverMigrate';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();
  const router = useRouter();

  const pagination = reactive({
    count: 100,
    current: 1,
    limit: 10,
  });

  const searchKeyword = ref('');

  const { loading: isLoading, data, run: fetchList } = useRequest(getList);

  const handelChange = (value: string) => {
    fetchList({
      cluster_name: value,
    });
  };

  const handleForcedTermination = (data: MigrateRecordModel) =>
    forceFailedMigrate({
      dts_id: data.id,
    }).then(() => {
      messageSuccess(t('操作成功'));
      fetchList({
        cluster_name: searchKeyword.value,
      });
    });

  const handleStopSync = (data: MigrateRecordModel) =>
    manualTerminateSync({
      ticket_id: data.ticket_id,
    }).then((data) => {
      fetchList({
        cluster_name: searchKeyword.value,
      });

      const {href} = router.resolve({
        name: 'SelfServiceMyTickets',
        query: {
          id: data.ticket_id,
        }
      })
      InfoBox({
        title: t('操作成功'),
        content: () => (
          <div>
            提交成功，请可前往“<a href={href} target="_blank">单据</a>”确认执行
          </div>
        ),
        type: 'success',
        onConfirm(){
          window.open(href)
        }
      })
    });
</script>
