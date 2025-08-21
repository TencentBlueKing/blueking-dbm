// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package pkgversion

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	actorCst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/inforeport/configreport"
)

func CollectPkgVersion() error {
	report, err := configreport.GetMixedReport("pkg_version.log")
	if err != nil {
		return err
	}
	binaries := map[string]string{
		"dbbackup":             filepath.Join(actorCst.DbbackupGoInstallPath, "dbbackup"),
		"rotatebinlog":         filepath.Join(actorCst.MysqlRotateBinlogInstallPath, "rotatebinlog"),
		"mysql-monitor":        filepath.Join(actorCst.MySQLMonitorInstallPath, "mysql-monitor"),
		"mysql-table-checksum": filepath.Join(actorCst.ChecksumInstallPath, "mysql-table-checksum"),
		"mysql-crond":          filepath.Join(actorCst.MySQLCrondInstallPath, "mysql-crond"),
		"backup_client":        filepath.Join(actorCst.BackupClientInstallPath, "bin", "backup_client"),
		//"dbactuator":           filepath.Join(actorCst.DBAToolkitPath, "dbactuator"),
		"gomysqlbinlog": filepath.Join(actorCst.DBAToolkitPath, "gomysqlbinlog"),
	}
	//var pkgs []*PkgVersion
	for pkgName, pkgPath := range binaries {
		if config.MonitorConfig.MachineType == "spider" &&
			(pkgName == "rotatebinlog" || pkgName == "mysql-table-checksum") {
			continue
		}
		var onePkg = &PkgVersion{
			PkgName: pkgName,
			PkgPath: pkgPath,
		}
		if pkgName == "gomysqlbinlog" {
			var anyPkg anyPackage = &gomysqlbinlogPkg{}
			onePkg = anyPkg.GetPkgVersion(pkgPath)
		} else if outStr, errStr, err := cmutil.ExecCommand(false, "", pkgPath, "version"); err != nil {
			onePkg.Msg = fmt.Sprintf("run %s: %v, out: %s, err: %s", pkgName, err, outStr, errStr)
		} else {
			if pkgVer, err := parseCommonVersion(outStr); err != nil {
				onePkg.Msg = err.Error()
			} else {
				onePkg.Version = pkgVer.Version
				onePkg.GitHash = pkgVer.GitHash
				onePkg.BuildAt = pkgVer.BuildAt
			}
		}
		event := configreport.NewDynamicEvent("pkg_version", "tendbha", 1)
		event.SetPayload(onePkg)
		report.Println(event)
	}
	return nil
}

// parseCommonVersion 解析版本信息
// Version: 0.3.2, GitHash: , BuildAt:
func parseCommonVersion(versionStr string) (*PkgVersion, error) {
	regVer := regexp.MustCompile(`Version: ([.\d]*), GitHash: (\w*), BuildAt:(.*)`)
	regVersion := regVer.FindStringSubmatch(versionStr)
	onePkg := PkgVersion{}
	if len(regVersion) > 3 {
		onePkg.Version = regVersion[1]
		onePkg.GitHash = regVersion[2]
		onePkg.BuildAt = strings.TrimSpace(regVersion[3]) // to time?
	} else {
		return nil, errors.Errorf("parse version failed: %s", versionStr)
	}
	return &onePkg, nil
}

type gomysqlbinlogPkg struct {
}

func (p *gomysqlbinlogPkg) PkgName() string {
	return "gomysqlbinlog"
}

func (p *gomysqlbinlogPkg) GetPkgVersion(pkgPath string) *PkgVersion {
	var onePkg = &PkgVersion{
		PkgName: p.PkgName(),
		PkgPath: pkgPath,
	}
	if outStr, errStr, err := cmutil.ExecCommand(false, "", pkgPath, "--version"); err != nil {
		onePkg.Msg = fmt.Sprintf("run %s: %v, out: %s, err: %s", p.PkgName(), err, outStr, errStr)
	} else {
		verReg := regexp.MustCompile(`gomysqlbinlog version (\S+)`)
		m := verReg.FindStringSubmatch(outStr)
		if len(m) > 1 {
			onePkg.Version = m[1]
		} else {
			onePkg.Msg = fmt.Sprintf("parse version failed: %s", outStr)
		}
	}
	return onePkg
}
