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
  <div class="db-copyright">
    <div class="contact">
      <a
        href="wxwork://message?uin=8444252571319680;"
        target="_blank">
        {{ $t('联系BK助手') }}
      </a>
      |
      <a
        href="https://bk.tencent.com/"
        target="_blank">
        {{ $t('蓝鲸桌面') }}
      </a>
    </div>
    <p class="copyright">
      Copyright © 2012-{{ currentYear }} Tencent BlueKing. All Rights Reserved. {{ version }}
    </p>
  </div>
</template>

<script setup lang="ts">
  import { getProjectVersion } from '@services/common';

  const currentYear = new Date().getFullYear();
  const version = ref('V1.0.0');

  getProjectVersion()
    .then((res) => {
      version.value = res.version;
    });
</script>

<style lang="less">
.db-copyright {
  display: flex;
  height: 52px;
  margin-top: 20px;
  font-size: 12px;
  line-height: 20px;
  color: #63656e;
  border-top: 1px solid #dcdee5;
  align-items: center;
  flex-direction: column;
  justify-content: center;
}
</style>
