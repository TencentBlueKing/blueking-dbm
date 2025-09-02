package import_grants_file

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/listener"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type ImportGrantsFile struct {
	GeneralParam            *components.GeneralParam `json:"general"`
	Params                  *ImportGrantsFileParam   `json:"extend"`
	importGrantsFileContext `json:"-"`
}

type ImportGrantsFileParam struct {
	BillId        string   `json:"bill_id"`
	SourceIp      string   `json:"source_ip"`
	SourceVersion string   `json:"source_version"`
	DestAddress   string   `json:"dest_address"`
	Filename      string   `json:"filename"`
	IgnoreUsers   []string `json:"ignore_users"`
	MachineType   string   `json:"machine_type"`
}

type importGrantsFileContext struct {
	db                 *native.DbWorker
	sourceRawVersion   string
	sourceMajorVersion uint64
	destRawVersion     string
	destMajorVersion   uint64
	workDir            string
	destIp             string
	destPort           int
	finalListeners     []*listener.PrivListener
	finalFilename      string
	lineCount          int
}

func (c *ImportGrantsFile) Init() (err error) {
	c.Params.IgnoreUsers = append(c.Params.IgnoreUsers, fmt.Sprintf("J_%s", c.Params.BillId))
	c.Params.IgnoreUsers = append(
		c.Params.IgnoreUsers,
		[]string{
			"mysql.session",
			"mysql.sys",
			"mysql.infoschema",
			"PUBLIC",
			"GM",
			"mariadb.sys",
			"spider",
			"gcs_spider",
			"gcs_admin",
			"gcs_dba",
			"mysql",
		}...,
	)

	logger.Info("ignore users: %v", c.Params.IgnoreUsers)

	splitDestAddress := strings.Split(c.Params.DestAddress, ":")
	c.destIp = splitDestAddress[0]
	c.destPort, err = strconv.Atoi(splitDestAddress[1])
	if err != nil {
		err = fmt.Errorf("%s is not a valid address", c.Params.DestAddress)
		return err
	}

	bin, err := os.Executable()
	if err != nil {
		return err
	}
	c.workDir = filepath.Dir(bin)

	//if (c.Params.SourceMachineType == "spider" && c.Params.DestMachineType != "spider") ||
	//	(c.Params.SourceMachineType != "spider" && c.Params.DestMachineType == "spider") {
	//	err = fmt.Errorf("can't clone between source %s and desc %s",
	//		c.Params.SourceMachineType, c.Params.DestMachineType,
	//	)
	//	return err
	//}

	c.db, err = native.InsObject{
		Host: c.destIp,
		Port: c.destPort,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		return err
	}

	v, err := c.db.SelectVersion()
	if err != nil {
		return err
	}

	c.destRawVersion = v
	c.sourceRawVersion = c.Params.SourceVersion

	if c.Params.MachineType == "spider" {
		c.destMajorVersion = cmutil.SpiderVersionParse(v)
		c.sourceMajorVersion = cmutil.SpiderVersionParse(c.sourceRawVersion) / 1000 * 1000
	} else {
		c.destMajorVersion = cmutil.MySQLVersionParse(v) / 1000 * 1000
		c.sourceMajorVersion = cmutil.MySQLVersionParse(c.sourceRawVersion) / 1000 * 1000
	}

	if c.sourceMajorVersion > c.destMajorVersion {
		err = fmt.Errorf(
			"source version %s is greater than dest version %s", c.sourceRawVersion, c.destRawVersion)
		return err
	}
	return nil
}
