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
  <DemandInfo
    :config="config"
    :data="ticketDetails" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { useCopy } from '@hooks';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import DemandInfo from '../../components/DemandInfo.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.DumpData>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy()

  const { cluster_id: clusterId, clusters, databases, tables, tables_ignore: tableIgnore, where, dump_data: dumpData, dump_schema: dumpSchema } = props.ticketDetails.details
  const domain = clusters[clusterId].immute_domain

  const config = [
    {
      list: [
        {
          label: t('目标集群'),
          render: () => (
            <TextOverflowLayout>
              {{
                default: () => domain,
                append: () => (
                  <bk-button
                    class="ml-4"
                    theme="primary"
                    text
                    onClick={() => handleCopy(domain)}>
                    <db-icon type="copy" />
                  </bk-button>
                ),
              }}
            </TextOverflowLayout>
          )
        },
        {
          label: t('目标 DB'),
          render: () => (
            <div>
              {
                databases.map((database) => <bk-tag class="mb-4">{database}</bk-tag>)
              }
              <bk-button
                class="ml-4"
                theme="primary"
                text
                onClick={() => handleCopy(databases.join('\n'))}>
                <db-icon type="copy" />
              </bk-button>
            </div>
          )
        },
        {
          label: t('目标表名'),
          render: () => (
            <TextOverflowLayout>
              {{
                default: () => tables.join(','),
                append: () => (
                  <bk-button
                    class="ml-4"
                    theme="primary"
                    text
                    onClick={() => handleCopy(tables.join('\n'))}>
                    <db-icon type="copy" />
                  </bk-button>
                ),
              }}
            </TextOverflowLayout>
          )
        },
        {
          label: t('忽略表名'),
          render: () => (
            <TextOverflowLayout>
              {{
                default: () => tableIgnore.join(',') || '--',
                append: () => (
                  tableIgnore.length > 0 && (
                    <bk-button
                      class="ml-4"
                      theme="primary"
                      text
                      onClick={() => handleCopy(tableIgnore.join('\n'))}>
                      <db-icon type="copy" />
                    </bk-button>
                  )
                ),
              }}
            </TextOverflowLayout>
          )
        },
        {
          label: t('where 条件'),
          iswhole: true,
          render: () => (
            where ? (
              <div>
                { where }
                <bk-button
                  class="ml-4"
                  theme="primary"
                  text
                  onClick={() => handleCopy(where)}>
                  <db-icon type="copy" />
                </bk-button>
              </div>
              ) : '--'
          )
        },
        {
          label: t('导出数据'),
          render: () => {
            let exportType = ''
            if (dumpData && dumpSchema) {
              exportType = t('数据和表结构')
            } else if (dumpData && !dumpSchema) {
              exportType = t('数据')
            } else {
              exportType = t('表结构')
            }
            return <span>{exportType}</span>
          }
        },
        {
          label: t('导出原因'),
          key: 'remark',
        },
      ],
    },
  ];

  const handleCopy = (value: string) => {
    copy(value)
  }
</script>
