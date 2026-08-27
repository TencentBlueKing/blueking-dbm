<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
-->

<template>
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="
        t(
          'DTS 数据迁移：按库表将数据从源集群迁到目标集群，一行对应一对源与目标。同名迁移目标库与源库同名，库表支持通配；库改名迁移按整库指定目标库名。库级克隆请使用「MySQL DB 数据克隆」。',
        )
      " />
    <BkForm
      class="mb-24 toolbox-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('迁移方式')"
        required>
        <CardCheckbox
          v-model="formData.migrateMethod"
          :desc="t('目标库与源库同名，支持按库表筛选和通配')"
          icon="bk-dbm-icon db-icon-copy"
          :title="t('同名迁移')"
          true-value="MYSQL_DTS_DATA_MIGRATE" />
        <CardCheckbox
          v-model="formData.migrateMethod"
          class="ml-8"
          :desc="t('逐库指定目标库名，按整库迁移')"
          icon="bk-dbm-icon db-icon-edit"
          :title="t('库改名迁移')"
          true-value="MYSQL_DTS_DATA_MIGRATE_RENAME" />
      </BkFormItem>
      <slot />
    </BkForm>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const formData = reactive({
    migrateMethod: (route.meta.ticketType as TicketTypes) || TicketTypes.MYSQL_DTS_DATA_MIGRATE,
  });

  watch(
    () => formData.migrateMethod,
    (val) => {
      if (val !== route.meta.ticketType) {
        router.push({ name: val });
      }
    },
  );
</script>
