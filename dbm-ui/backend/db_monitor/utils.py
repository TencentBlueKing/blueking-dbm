"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import re


def render_promql_sql(prom_sql, wheres):
    """
    Modify a PromQL query by replacing existing label conditions, or adding new ones if they do not exist.

    Parameters:
    original_sql (str): The original PromQL query.
    new_conditions (dict): A dictionary of conditions to add or replace in the form {label: value or list of values}.

    Returns:
    str: The modified PromQL query.
    """
    for label, value in wheres.items():
        # If the value is a list, convert it to a regex alternation pattern
        value = value[0] if isinstance(value, list) and len(value) == 1 else value

        # skip empty list
        if not value:
            continue

        if isinstance(value, list):
            value = f'({"|".join(map(str, value))})'
            value = f'~"{value}"'  # Use the regex match operator '~'
        else:
            value = f'"{value}"'

        # Check if label already exists in the query
        if re.search(fr'{label}="[^"]*"|\b{label}=~"[^"]*"', prom_sql):
            # If label exists, replace its value
            prom_sql = re.sub(fr'{label}="[^"]*"|\b{label}=~"[^"]*"', fr"{label}={value}", prom_sql)
        else:
            # If label does not exist, add before the closing '}'
            # Use double }} to escape a single } in the f-string
            prom_sql = re.sub(r"}", f", {label}={value}}}", prom_sql)

    return prom_sql


if __name__ == "__main__":
    sql = """ioutil{cluster_type="a"}[1m] by cpu{appid="5"} by disk{db_module="2"}"""
    # Conditions to modify or add to the original SQL query
    new_conditions = {"appid": ["2", "3"], "cluster_domain": ["hello.2"], "db_module": ["1"]}
    # Render the modified PromQL query
    print(render_promql_sql(sql, new_conditions))
