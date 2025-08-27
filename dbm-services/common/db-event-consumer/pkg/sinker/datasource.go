// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"os"

	"github.com/go-viper/mapstructure/v2"
	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

type Datasource struct {
	Name string                 `yaml:"name"`
	Type string                 `yaml:"type"`
	Dsn  map[string]interface{} `yaml:"dsn" json:"dsn"`
}

var DatasourceMap = make(map[string]*Datasource)

func InitDatasource() error {
	datasourceFile := "datasource.yaml"
	var dsAll []*Datasource
	content, err := os.ReadFile(datasourceFile)
	if err != nil {
		return err
	}
	if err = yaml.Unmarshal(content, &dsAll); err != nil {
		os.Stderr.WriteString(err.Error())
		return err
	}
	for _, d := range dsAll {
		if _, ok := ModelWriterType[d.Type]; !ok {
			return errors.Errorf("unknown datasource type %s", d.Type)
		}
		if _, ok := DatasourceMap[d.Name]; ok {
			return errors.Errorf("duplicate datasource name %s", d.Name)
		}
		DatasourceMap[d.Name] = d
	}
	return nil
}

type InstanceDsn struct {
	User             string                 `yaml:"user"`
	Password         string                 `yaml:"password"`
	Address          string                 `yaml:"address"`
	Database         string                 `yaml:"database"`
	Charset          string                 `yaml:"charset"`
	SessionVariables map[string]interface{} `yaml:"session_variables" mapstructure:"session_variables"`
}

func GetDSWriter(ds *Datasource) (DSWriter, error) {
	if ds.Type == "mysql" {
		var mysqlDsn InstanceDsn
		if err := mapstructure.Decode(ds.Dsn, &mysqlDsn); err != nil {
			return nil, errors.WithMessagef(err, "decode dsn %s", ds.Dsn)
		}
		return NewMysqlWriter(&mysqlDsn, nil)
	} else if ds.Type == "mysql_xorm" {
		var mysqlDsn InstanceDsn
		if err := mapstructure.Decode(ds.Dsn, &mysqlDsn); err != nil {
			return nil, errors.WithMessagef(err, "decode dsn %s", ds.Dsn)
		}
		return NewXormWriter(&mysqlDsn, nil)
	} else if ds.Type == "doris" {
		return NewMysqlWriter(nil, nil)
	} else {
		return nil, errors.Errorf("unknown datasource type %s", ds.Type)
	}
}
