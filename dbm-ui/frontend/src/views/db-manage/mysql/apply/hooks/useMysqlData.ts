/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import InfoBox from 'bkui-vue/lib/info-box';
import _ from 'lodash';
import { useI18n } from 'vue-i18n';

import { getInfrasHostSpecs } from '@services/source/infras';
import type { HostInfo } from '@services/types';

import { Affinity, type MysqlTypeString } from '@common/const';

type FetchState = {
  hostSpecs: ServiceReturnType<typeof getInfrasHostSpecs>;
};

const getFormData = (type: string) => ({
  bk_biz_id: '' as '' | number,
  details: {
    bk_cloud_id: 0,
    charset: '',
    city_code: '',
    cluster_count: 1,
    db_app_abbr: '',
    db_module_id: null as null | number,
    disaster_tolerance_level: Affinity.NONE, // 同 affinity
    domains: [{ key: '' }],
    inst_num: 1,
    ip_source: 'resource_pool',
    nodes: {
      backend: [] as HostInfo[],
      proxy: [] as HostInfo[],
    },
    resource_spec: {
      backend: {
        affinity: '',
        count: 0,
        location_spec: {
          city: '',
          sub_zone_ids: [],
        },
        spec_id: '' as string | number,
      },
      proxy: {
        count: 0,
        spec_id: '' as string | number,
      },
      single: {
        count: 0,
        location_spec: {
          city: '',
          sub_zone_ids: [],
        },
        spec_id: '' as string | number,
      },
    },
    spec: '',
    start_mysql_port: 20000,
    start_proxy_port: 10000,
    sub_zone_ids: [] as number[],
  },
  remark: '',
  ticket_type: type,
});

export const useMysqlData = (type: string) => {
  const route = useRoute();
  const { t } = useI18n();

  const ticketType = type as MysqlTypeString;
  const formdata = reactive(getFormData(ticketType));
  // 接口数据
  const fetchState = reactive<FetchState>({
    hostSpecs: [],
  });

  /**
   * 设置 domain 数量
   */
  watch(
    () => formdata.details.cluster_count,
    (count: number) => {
      if (count > 0 && count <= 200) {
        const len = formdata.details.domains.length;
        if (count > len) {
          const appends = Array.from({ length: count - len }, () => ({ key: '' }));
          formdata.details.domains.push(...appends);
          return;
        }
        if (count < len) {
          formdata.details.domains.splice(count - 1, len - count);
          return;
        }
      }
    },
  );

  // /**
  //  * 获取配置详情下拉展示
  //  */
  // const fetchLevelConfig = (moduleId: number) => {
  //   const params = {
  //     bk_biz_id: formdata.bk_biz_id as number,
  //     conf_type: 'deploy',
  //     level_name: 'module',
  //     level_value: moduleId,
  //     meta_cluster_type: mysqlType[ticketType].type,
  //     version: 'deploy_info',
  //   };
  //   loading.levelConfigs = true;
  //   getLevelConfig(params)
  //     .then((res) => {
  //       fetchState.levelConfigList = res.conf_items;
  //     })
  //     .finally(() => {
  //       loading.levelConfigs = false;
  //     });
  // };

  /**
   * 查询层级（业务、模块、集群）配置详情
   */
  // watch(
  //   () => formdata.details.db_module_id,
  //   (value) => {
  //     if (value) {
  //       fetchLevelConfig(value);
  //     }
  //   },
  // );

  /**
   * 获取服务器规格列表
   */
  watch(
    () => formdata.details.city_code,
    (value: string) => {
      if (value) {
        formdata.details.spec = '';
        fetchInfrasHostSpecs();
      }
    },
  );
  const fetchInfrasHostSpecs = () => {
    getInfrasHostSpecs().then((res) => {
      fetchState.hostSpecs = res || [];
    });
  };

  // /**
  //  * 获取模块列表
  //  */
  // watch(
  //   () => formdata.bk_biz_id,
  //   (value) => {
  //     if (value) {
  //       fetchModules(value);
  //     }
  //   },
  // );
  // const fetchModules = (bizId: number | null) => {
  //   if (!bizId) {
  //     return;
  //   }

  //   loading.modules = true;
  //   const params = {
  //     bk_biz_id: bizId,
  //     cluster_type: mysqlType[ticketType].type,
  //   };
  //   getModules(params)
  //     .then((res) => {
  //       fetchState.moduleList = res || [];
  //     })
  //     .finally(() => {
  //       loading.modules = false;
  //     });
  // };

  /**
   * reset formdata
   */
  const handleResetFormdata = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        _.merge(formdata, getFormData(route.params.type as string));
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
    });
  };

  /**
   * 创建单据
   */
  // const submitTicket = () => createTicket(formdata);

  return {
    fetchState,
    formdata,
    // loading,
    // leveConfig,
    // submitTicket,
    handleResetFormdata,
    // fetchModules,
    // fetchLevelConfig,
  };
};
