<template>
  <TicketInfoTable
    class="preview-privilege-table"
    :data="tableData"
    row-key="user">
    <TicketInfoTableColumn
      col-key="ips"
      :get-copy-value="(row: IDataRow) => row.ips"
      :min-width="150"
      :title="t('访问源')">
      <template #default="{ row }: { row: IDataRow }">
        <div>
          <p
            v-for="(ip, index) in showAllIp ? row.ips : row.ips.slice(0, 10)"
            :key="index">
            {{ ip }}
          </p>
        </div>
        <div v-if="row.ips.length > 10">
          <DbTag size="small">
            {{ t('共n个', [row.ips.length]) }}
          </DbTag>
          <BkButton
            class="more-btn"
            text
            theme="primary"
            @click="() => (showAllIp = !showAllIp)">
            {{ showAllIp ? t('收起') : t('更多') }}
          </BkButton>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="clusterDomains"
      :get-copy-value="(row: IDataRow) => row.clusterDomains"
      :min-width="250"
      :title="t('集群域名')">
      <template #default="{ row }: { row: IDataRow }">
        <div class="cell-cluster">
          <p
            v-for="(item, index) in row.clusterDomains"
            :key="index">
            {{ item }}
          </p>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="user"
      :title="t('账号')" />
    <TicketInfoTableColumn
      col-key="accessDbs"
      :min-width="150"
      :title="t('访问DB')">
      <template #default="{ row }: { row: IDataRow }">
        <div>
          <p
            v-for="item in showAllDb ? row.accessDbs : row.accessDbs.slice(0, 10)"
            :key="item"
            class="mb-6">
            <DbTag>
              {{ item }}
            </DbTag>
          </p>
        </div>
        <div v-if="row.accessDbs.length > 10">
          <DbTag size="small">
            {{ t('共n个', [row.accessDbs.length]) }}
          </DbTag>
          <BkButton
            class="more-btn"
            text
            theme="primary"
            @click="() => (showAllDb = !showAllDb)">
            {{ showAllDb ? t('收起') : t('更多') }}
          </BkButton>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="privilege"
      :min-width="400"
      :title="t('权限')">
      <template #default="{ row }: { row: IDataRow }">
        <div
          v-for="(privilege, key) in userDbPrivilegeMap[row.user]"
          :key="key">
          <div
            v-if="privilege.length"
            class="cell-privilege">
            <div style="font-weight: bold">{{ key === 'glob' ? t('全局') : key.toUpperCase() }} :</div>
            <div class="cell-privilege-value">
              <span
                v-for="(item, index) in privilege"
                :key="index"
                class="cell-privilege-item">
                {{ index !== 0 ? ',' : '' }}
                {{ item }}
                <span
                  v-if="ddlSensitiveWordsMap[item]"
                  class="sensitive-tip">
                  {{ t('敏感') }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryAccountRules } from '@services/source/mongodbPermissionAccount';
  import type { AccountRulePrivilege, AuthorizePreCheckData } from '@services/types';

  import { AccountTypes } from '@common/const';

  import configMap from '@views/db-manage/common/permission/components/mysql/config';

  interface IDataRow {
    accessDbs: string[];
    clusterDomains: string[];
    ips: string[];
    privileges?: AuthorizePreCheckData['privileges'];
    user: string;
  }

  interface Props {
    accountType: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
    data: IDataRow[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const showAllIp = ref(false);
  const showAllDb = ref(false);
  const tableData = shallowRef<IDataRow[]>([]);
  const userDbPrivilegeMap = shallowRef<Record<string, AccountRulePrivilege>>({});

  const ddlSensitiveWordsMap = computed(() =>
    Object.fromEntries(configMap[props.accountType].ddlSensitiveWords.map((word) => [word, true])),
  );

  watch(
    () => props.data,
    () => {
      tableData.value = props.data;

      const { dbOperations: { ddl = [], dml = [], glob = [] } = {} } = configMap[props.accountType];

      // 若权限快照存在
      if (props.data[0].privileges?.length) {
        userDbPrivilegeMap.value = props.data.reduce<Record<string, AccountRulePrivilege>>((acc, cur) => {
          const { privileges } = cur;
          privileges?.forEach((item) => {
            const { priv, user } = item;
            const privileageMap = new Set(priv.split(','));
            Object.assign(acc, {
              [user]: {
                ddl: ddl.filter((item) => privileageMap.has(item)),
                dml: dml.filter((item) => privileageMap.has(item)),
                glob: glob.filter((item) => privileageMap.has(item)),
              },
            });
          });
          return acc;
        }, {});
        return;
      }

      /**
       * 兼容老数据
       * 异步查询权限
       */
      Promise.all(
        props.data.map(
          ({ accessDbs, user }) =>
            new Promise<Record<string, AccountRulePrivilege>>((resolve, reject) => {
              queryAccountRules({
                access_dbs: accessDbs,
                account_type: props.accountType,
                user,
              }).then(({ results }) => {
                if (results.length === 0) {
                  reject(new Error('未查询到权限信息'));
                  return;
                }
                const privileageMap = new Set(results[0].rules.flatMap((item) => item.privilege.split(',')));
                resolve({
                  [user]: {
                    ddl: ddl.filter((item) => privileageMap.has(item)),
                    dml: dml.filter((item) => privileageMap.has(item)),
                    glob: glob.filter((item) => privileageMap.has(item)),
                  },
                });
              });
            }),
        ),
      ).then((data) => {
        userDbPrivilegeMap.value = data.reduce((acc, cur) => ({ ...acc, ...cur }), {});
      });
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .preview-privilege-table {
    :deep(td) {
      padding: 4px 16px !important;
      line-height: 20px !important;

      .db-icon-copy {
        display: none;
        color: @primary-color;
        cursor: pointer;
      }

      .more-btn {
        display: none;
      }

      &:hover {
        .db-icon-copy,
        .more-btn {
          display: inline-block;
        }
      }

      .cell-cluster {
        line-height: 28px;
      }

      .cell-privilege {
        display: flex;

        .cell-privilege-value {
          max-width: 350px;
          margin-left: 6px;
          overflow-wrap: break-word;
          white-space: normal;
        }
      }

      .sensitive-tip {
        height: 16px;
        padding: 0 4px;
        margin-left: 4px;
        font-size: 10px;
        line-height: 16px;
        color: #fe9c00;
        text-align: center;
        background: #fff3e1;
        border-radius: 2px;
      }
    }
  }
</style>
