<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkButton @click="handleShow">
    {{ t('权限预览') }}
  </BkButton>
  <BkDialog
    :draggable="false"
    :is-show="isShow"
    :quick-close="false"
    :title="t('预览权限')"
    :width="1200"
    @closed="handleClose">
    <BkTable
      class="preview-privilege-table"
      :data="tableData">
      <BkTableColumn
        :label="t('访问源')"
        :width="150">
        <template #default="{ data: rowData }: { data: IDataRow }">
          <div>
            <p
              v-for="(ip, index) in showAllIp ? rowData.ips : rowData.ips.slice(0, 10)"
              :key="index">
              {{ ip }}
              <DbIcon
                v-if="index === 0"
                type="copy"
                @click="handleCopyIps" />
            </p>
          </div>
          <div v-if="rowData.ips.length > 10">
            <BkTag size="small">
              {{ t('共n个', [rowData.ips.length]) }}
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
        <template #default="{ data: rowData }: { data: IDataRow }">
          <div class="cell-cluster">
            <p
              v-for="(item, index) in rowData.clusterDomains"
              :key="index">
              {{ item }}
              <DbIcon
                v-if="index === 0"
                type="copy"
                @click="handleCopyDomains" />
            </p>
          </div>
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('账号')"
        prop="account"
        :width="150" />
      <BkTableColumn
        :label="t('访问DB')"
        :width="150">
        <template #default="{ data: rowData }: { data: IDataRow }">
          <div>
            <p
              v-for="item in showAllDb ? rowData.accessDbs : rowData.accessDbs.slice(0, 10)"
              :key="item"
              class="mb-6">
              <BkTag>
                {{ item }}
              </BkTag>
            </p>
          </div>
          <div v-if="rowData.accessDbs.length > 10">
            <BkTag size="small">
              {{ t('共n个', [rowData.accessDbs.length]) }}
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
        :width="350">
        <template #default="{ data: rowData }: { data: IDataRow }">
          <div
            v-for="(privilege, key) in rowData.privilege"
            :key="`${rowData.account}#${key}`">
            <div
              v-if="privilege.length > 0"
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
    <template #footer>
      <BkButton @click="handleClose">{{ t('关闭') }}</BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { AccountRulePrivilege, PermissionRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  import configMap from '@views/db-manage/common/permission/components/mysql/config';

  import { execCopy } from '@utils';

  interface Props {
    accountType: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
    data: {
      source_ips: {
        ip: string;
        bk_host_id: number;
        bk_biz_id: number;
      }[];
      target_instances: string[];
      user: string;
      access_dbs: string[];
      rules: PermissionRule['rules'];
    };
  }

  interface IDataRow {
    ips: string[];
    account: string;
    accessDbs: string[];
    clusterDomains: string[];
    privilege: AccountRulePrivilege;
  }

  const props = defineProps<Props>();

  const isShow = ref(false);

  const { t } = useI18n();

  const showAllIp = ref(false);
  const showAllDb = ref(false);
  const tableData = shallowRef<IDataRow[]>([]);
  let ddlSensitiveWordsMap: Record<string, boolean> = {};

  watch(isShow, () => {
    if (isShow.value && props.data.rules.length > 0) {
      const { dbOperations: { ddl = [], dml = [], glob = [] } = {}, ddlSensitiveWords = [] } =
        configMap[props.accountType];
      ddlSensitiveWordsMap = Object.fromEntries(ddlSensitiveWords.map((word) => [word, true]));

      const privileges = props.data.rules.reduce<string[]>((acc, item) => [...acc, ...item.privilege.split(',')], []);

      const privileageMap = Object.fromEntries(privileges.map((priv) => [priv, true]));

      tableData.value = [
        {
          ips: props.data.source_ips.map((item) => item.ip),
          account: props.data.user,
          accessDbs: props.data.access_dbs,
          clusterDomains: props.data.target_instances,
          privilege: {
            ddl: ddl.filter((item) => privileageMap[item]),
            dml: dml.filter((item) => privileageMap[item]),
            glob: glob.filter((item) => privileageMap[item]),
          },
        },
      ];
    }
  });

  const handleShow = () => {
    isShow.value = true;
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleCopyIps = () => {
    const ips = props.data.source_ips.map((item) => item.ip);
    execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
  };

  const handleCopyDomains = () => {
    const domians = props.data.target_instances;
    execCopy(domians.join('\n'), t('复制成功，共n条', { n: domians.length }));
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
