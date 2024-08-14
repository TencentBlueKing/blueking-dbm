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
        <template #default="{ data }: { data: IDataRow }">
          <div>
            <p
              v-for="(ip, index) in showAllIp ? data.ips : data.ips.slice(0, 10)"
              :key="index">
              {{ ip }}
              <DbIcon
                v-if="index === 0"
                type="copy"
                @click="handleCopyIps" />
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
        :label="t('账号')"
        prop="account"
        :width="150" />
      <BkTableColumn
        :label="t('访问的DB')"
        :width="150">
        <template #default="{ data }: { data: IDataRow }">
          <BkTag>{{ data.accessDb }}</BkTag>
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('集群域名')"
        :width="250">
        <template #default="{ data }: { data: IDataRow }">
          <div class="cell-cluster">
            <p
              v-for="(cluster, index) in data.clusters"
              :key="index">
              {{ cluster.master_domain }}
              <DbIcon
                v-if="index === 0"
                type="copy"
                @click="handleCopyDomains" />
            </p>
          </div>
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('权限')"
        :width="350">
        <template #default="{ data }: { data: IDataRow }">
          <div
            v-for="(privilege, key) in data.privilege"
            :key="`${data.accessDb}#${key}`">
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

  import { useCopy } from '@hooks';

  import { DBTypes } from '@common/const';

  import { configMap, type RuleSettingsConfig } from '../create-rule/Index.vue';

  interface Props {
    data: {
      ips: string[];
      account: string;
      clusters: {
        id: number;
        master_domain: string;
        slave_domain: string;
      }[];
      rules: {
        access_db: string;
        account_id: number;
        privilege: string;
        rule_id: number;
      }[];
    };
  }

  interface IDataRow {
    ips: string[];
    account: string;
    accessDb: string;
    clusters: Props['data']['clusters'];
    privilege: {
      ddl: string[];
      dml: string[];
      glob: string[];
    };
  }

  interface Emits {
    (e: 'close'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const copy = useCopy();

  const showAllIp = ref(false);
  const tableData = shallowRef<IDataRow[]>([]);
  let ddlSensitiveWordsMap: Record<string, boolean> = {};

  watch(isShow, () => {
    if (isShow.value) {
      const { dbOperations: { ddl = [], dml = [], glob = [] } = {}, ddlSensitiveWords = [] } = configMap[
        DBTypes.MYSQL
      ] as RuleSettingsConfig;
      ddlSensitiveWordsMap = Object.fromEntries(ddlSensitiveWords.map((word) => [word, true]));
      tableData.value = props.data.rules.map((cur) => {
        const privileageMap = Object.fromEntries(cur.privilege.split(',').map((priv) => [priv, true]));
        return {
          ips: props.data.ips,
          account: props.data.account,
          accessDb: cur.access_db,
          clusters: props.data.clusters,
          privilege: {
            ddl: ddl.filter((item) => privileageMap[item]),
            dml: dml.filter((item) => privileageMap[item]),
            glob: glob.filter((item) => privileageMap[item]),
          },
        };
      });
    }
  });

  const handleClose = () => {
    emits('close');
  };

  const handleCopyIps = () => {
    copy(props.data.ips.join('\n'));
  };

  const handleCopyDomains = () => {
    const domians = props.data.clusters.map((item) => item.master_domain).join('\n');
    copy(domians);
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
