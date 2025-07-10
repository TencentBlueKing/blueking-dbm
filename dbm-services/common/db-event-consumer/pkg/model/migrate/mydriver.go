// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package migrate

import (
	"fmt"
	"io"
	"strings"

	"github.com/golang-migrate/migrate/v4/source"

	"github.com/pkg/errors"
)

type MapDriver struct {
	migrations *source.Migrations
	migs       map[string]string
	//sortedMap  *smap.OrderedMap
}

func NewMapDriver(migs map[string]string) (source.Driver, error) {
	if len(migs) == 0 {
		return nil, errors.New("no migrations to run")
	}
	var i = MapDriver{migs: migs}
	//i.sortedMap = smap.NewOrderedMap[string, any]()

	ms := source.NewMigrations()
	for ver, e := range migs {
		m, err := source.DefaultParse(ver)
		if err != nil || e == "" {
			continue
		}
		if !ms.Append(m) {
			return nil, fmt.Errorf("migrations: duplicate version %q", ver)
		}
	}

	i.migrations = ms
	return &i, nil
}

func (d *MapDriver) Open(url string) (source.Driver, error) {
	return nil, errors.New("Open() cannot be called on the mapss driver")
	//return nil, nil
}

func (d *MapDriver) Close() error {
	return nil
}

func (d *MapDriver) First() (version uint, err error) {
	if version, ok := d.migrations.First(); ok {
		return version, nil
	}
	return 0, errors.New("no first migration found")
}

func (d *MapDriver) Prev(version uint) (prevVersion uint, err error) {
	if version, ok := d.migrations.Prev(version); ok {
		return version, nil
	}
	return 0, errors.New("no prev migration found")
}

func (d *MapDriver) Next(version uint) (nextVersion uint, err error) {
	if version, ok := d.migrations.Next(version); ok {
		return version, nil
	}
	return 0, errors.New("no next migration found")
}

func (d *MapDriver) ReadUp(version uint) (r io.ReadCloser, identifier string, err error) {
	if m, ok := d.migrations.Up(version); ok {
		body := io.NopCloser(strings.NewReader(d.migs[m.Raw]))
		return body, m.Identifier, nil
	}
	return nil, "", errors.New("no migration found")
}

func (d *MapDriver) ReadDown(version uint) (r io.ReadCloser, identifier string, err error) {
	if m, ok := d.migrations.Down(version); ok {
		body := io.NopCloser(strings.NewReader(d.migs[m.Raw]))
		return body, m.Identifier, nil
	}
	return nil, "", errors.New("no migration found")
}
