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

import { generateId } from './generateId';

import type {
  SearchSelectData,
  SearchSelectItem,
  SearchSelectValues,
} from '@/types/bkui-vue';

/**
 * search-select 组件搜索功能函数
 * @param searchItem data item
 * @param keyword search keyword
 * @param data search-select data
 * @param values search-select values
 * @param uniqueSelect search-select unique-select props
 * @returns menu list
 */
export function getMenuListSearch(
  searchItem: SearchSelectItem | undefined,
  keyword: string,
  data: SearchSelectData,
  values: SearchSelectValues,
  uniqueSelect = true,
) {
  const lowerCaseKeyword = keyword.toLocaleLowerCase();
  if (searchItem) {
    const { children, multiple } = searchItem;
    if (multiple && children?.length) {
      return children.filter(child => child.name.toLocaleLowerCase().includes(lowerCaseKeyword));
    }

    const resList = [{
      ...searchItem,
      realId: searchItem.id,
      id: generateId('MISSION_SEARCH_ID_'),
      value: {
        id: keyword,
        name: keyword,
      },
    }];
    if (children?.length) {
      const childList = children
        .filter(child => child.name.toLocaleLowerCase().includes(lowerCaseKeyword))
        .map(child => ({
          ...searchItem,
          realId: searchItem.id,
          id: generateId('MISSION_SEARCH_ID_'),
          value: child,
        }));
      resList.push(...childList);
    }

    return resList;
  }

  const selected = (values || []).map(value => value.id);
  const filterData = uniqueSelect ? data.filter(dataItem => !selected.includes(dataItem.id)) : data;
  return filterData.reduce((list: any[], dataItem) => {
    dataItem.children?.forEach((child) => {
      if (child.name.toLocaleLowerCase().includes(lowerCaseKeyword)) {
        list.push({
          ...dataItem,
          realId: dataItem.id,
          id: generateId('MISSION_SEARCH_ID_'),
          value: child,
        });
      }
    });
    list.push({
      ...dataItem,
      value: {
        id: keyword,
        name: keyword,
      },
    });
    return list;
  }, []);
}
