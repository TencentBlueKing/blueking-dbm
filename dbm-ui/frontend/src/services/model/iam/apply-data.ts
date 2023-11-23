/*
  TencentBlueKing is pleased to support the open source community by making
  蓝鲸智云 - 审计中心 (BlueKing - Audit Center) available.
  Copyright (C) 2023 THL A29 Limited,
  a Tencent company. All rights reserved.
  Licensed under the MIT License (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at http://opensource.org/licenses/MIT
  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on
  an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the License for the
  specific language governing permissions and limitations under the License.
  We undertake not to change the open source license (MIT license) applicable
  to the current version of the project delivered to anyone in the future.
*/
import _ from 'lodash';

interface IInstance {
  type: string,
  type_name: string,
  id: string,
  name: string,
}
interface IRelatedResourceType {
  system_id: string,
  system_name: string,
  type: string,
  type_name: string,
  instances: Array<Array<IInstance>>
}

type IRenderPermissionList = Array<{
  systemName: string,
  actionName: string,
  relatedResources: Array<{
    type: string,
    instances: Array<string>
  }>
}>

export default class ApplyData {
  apply_url: string;
  permission: {
    system_id: string;
    system_name: string;
    actions: Array<{
      id: string,
      name: string,
      related_resource_types: Array<IRelatedResourceType>
    }>
  };

  constructor(payload = {} as ApplyData) {
    this.apply_url = payload.apply_url || '';
    this.permission = payload.permission || {};
  }

  get hasPermission() {
    return !this.apply_url;
  }

  get permissionList() {
    const systemName = this.permission.system_name;
    const stack = [] as IRenderPermissionList;
    this.permission.actions.forEach((action) => {
      const relatedResourceTypes: IRenderPermissionList[0]['relatedResources'] = [];
      action.related_resource_types.forEach((relateResource) => {
        const instances = relateResource.instances.reduce((result, instancePathList) => {
          const lastItem = _.last(instancePathList);
          if (lastItem) {
            result.push(lastItem.name);
          }
          return result;
        }, [] as Array<string>);
        relatedResourceTypes.push({
          type: relateResource.type_name,
          instances,
        });
      });
      stack.push({
        systemName,
        actionName: action.name,
        relatedResources: relatedResourceTypes,
      });
    });

    return stack;
  }
}
