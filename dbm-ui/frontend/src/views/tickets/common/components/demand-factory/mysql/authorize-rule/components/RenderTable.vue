<template>
  <BkTable
    class="preview-privilege-table"
    :data="tableData">
    <BkTableColumn
      :label="t('访问源')"
      :width="150">
      <template #default="{ data }: { data: IDataRow }">
        <div>
          <p
            v-for="(ip, index) in showAllIp ? data.ips : data.ips.slice(0, 10)"
            :key="index">
            {{ ip }}
            <DbIcon
              v-if="index === 0"
              type="copy"
              @click="() => handleCopyIps(data.ips)" />
          </p>
        </div>
        <div v-if="data.ips.length > 10">
          <BkTag size="small">
            {{ t('共n个', [data.ips.length]) }}
          </BkTag>
          <BkButton
            class="more-btn"
            text
            theme="primary"
            @click="() => (showAllIp = !showAllIp)">
            {{ showAllIp ? t('收起') : t('更多') }}
          </BkButton>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('集群域名')"
      :width="250">
      <template #default="{ data }: { data: IDataRow }">
        <div class="cell-cluster">
          <p
            v-for="(item, index) in data.clusterDomains"
            :key="index">
            {{ item }}
            <DbIcon
              v-if="index === 0"
              type="copy"
              @click="() => handleCopyDomains(data.clusterDomains)" />
          </p>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('账号')"
      prop="user" />
    <BkTableColumn
      :label="t('访问DB')"
      :width="150">
      <template #default="{ data }: { data: IDataRow }">
        <div>
          <p
            v-for="item in showAllDb ? data.accessDbs : data.accessDbs.slice(0, 10)"
            :key="item"
            class="mb-6">
            <BkTag>
              {{ item }}
            </BkTag>
          </p>
        </div>
        <div v-if="data.accessDbs.length > 10">
          <BkTag size="small">
            {{ t('共n个', [data.accessDbs.length]) }}
          </BkTag>
          <BkButton
            class="more-btn"
            text
            theme="primary"
            @click="() => (showAllDb = !showAllDb)">
            {{ showAllDb ? t('收起') : t('更多') }}
          </BkButton>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('权限')"
      :width="400">
      <template #default="{ data }: { data: IDataRow }">
        <div
          v-for="(privilege, key) in userDbPrivilegeMap[`${data.user}#${data.accessDbs}`]"
          :key="`${data.user}#${data.accessDbs}#${key}`">
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
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryAccountRules } from '@services/source/mongodbPermissionAccount';
  import type { AccountRulePrivilege, AuthorizePreCheckData } from '@services/types';

  import { useCopy } from '@hooks';

  import { AccountTypes } from '@common/const';

  import configMap from '@views/db-manage/common/permission/components/mysql/config';

  interface IDataRow {
    ips: string[];
    user: string;
    accessDbs: string[];
    clusterDomains: string[];
    privileges?: AuthorizePreCheckData['privileges'];
  }

  interface Props {
    accountType: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
    data: IDataRow[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();

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
            const { user, access_db: accessDbs, priv } = item;
            const privileageMap = new Set(priv.split(','));
            acc[`${user}#${accessDbs}`] = {
              ddl: ddl.filter((item) => privileageMap.has(item)),
              dml: dml.filter((item) => privileageMap.has(item)),
              glob: glob.filter((item) => privileageMap.has(item)),
            };
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
          ({ user, accessDbs }) =>
            new Promise<Record<string, AccountRulePrivilege>>((resolve) => {
              queryAccountRules({
                user,
                access_dbs: accessDbs,
                account_type: props.accountType,
              }).then(({ results }) => {
                const privileageMap = new Set(results[0].rules.flatMap((item) => item.privilege.split(',')));
                resolve({
                  [`${user}#${accessDbs}`]: {
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

  const handleCopyIps = (ips: string[]) => {
    copy(ips.join('\n'));
  };

  const handleCopyDomains = (domains: string[]) => {
    copy(domains.join('\n'));
  };
</script>

<style lang="less" scoped>
  .preview-privilege-table {
    :deep(.cell) {
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
          word-wrap: break-word;
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
