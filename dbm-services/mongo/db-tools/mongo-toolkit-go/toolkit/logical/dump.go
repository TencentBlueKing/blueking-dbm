package logical

import (
	"dbm-services/mongo/db-tools/dbmon/config"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/util"
	"fmt"
	"os"
	"path"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

// BakcupArgs 备份参数
type BakcupArgs struct {
	BackupNode  string `json:"backupNode"`
	IsPartial   bool   `json:"isPartial"` // 为true时，备份指定库和表
	Oplog       bool   `json:"oplog"`
	PartialArgs struct {
		DbList        []string `json:"dbList"`
		IgnoreDbList  []string `json:"ignoreDbList"`
		ColList       []string `json:"colList"`
		IgnoreColList []string `json:"ignoreColList"`
	} `json:"partialArgs"`
}

// DumpOption logical backup and restore
type DumpOption struct {
	MongodumpExePath   string
	MongoHost          *mymongo.MongoHost
	BackupType         string
	Dir                string
	Zip                bool
	SendToBackupSystem bool
	Tag                string // 备份文件Tag
	RemoveOldFileFirst bool
	ReportFile         string
	BkDbmLabel         *config.BkDbmLabel
	DryRun             bool
	Args               *BakcupArgs
}

// Dump 逻辑备份
func Dump(option *DumpOption) {
	log.Infof("start logical backup, option: %+v", option)
	helper := NewMongoDumpHelper(option.MongoHost, option.MongodumpExePath,
		option.MongoHost.User, option.MongoHost.Pass, option.MongoHost.AuthDb, "")

	// 备份目录
	tmpPath, _, err := getTmpSubDir(option.Dir, "mongodump")
	if err != nil {
		panic(err)
	}

	if option.Args.IsPartial {
		filter := NewNsFilter(option.Args.PartialArgs.DbList, option.Args.PartialArgs.IgnoreDbList,
			option.Args.PartialArgs.ColList, option.Args.PartialArgs.IgnoreColList)

		cmdLineList, cmdLine, err := helper.DumpPartial(tmpPath, "dump.log", filter)
		if err != nil {
			log.Errorf("exec cmd fail, cmd: %s, error:%s", cmdLine, err)
			return
		}
		log.Errorf("exec cmd success, cmd: %s", cmdLineList)
	} else {
		cmdLine, err := helper.LogicalDumpAll(tmpPath, "dump.log")
		if err != nil {
			log.Errorf("exec cmd fail, cmd: %s, error:%s", cmdLine, err)
			return
		}
		log.Errorf("exec cmd success, cmd: %s", cmdLine)
	}

	// 分析dump日志
	ns, err := checkDumpLog(path.Join(tmpPath, "dump.log"))
	if err != nil {
		log.Errorf("check dump log failed, err %v", err)
		return
	}
	log.Infof("dump ns: %+v", ns)

	tarFilePath, err := helper.Tar(tmpPath, true, true)
	if err != nil {
		log.Errorf("tar dir %s failed, err %v", tmpPath, err)
		return
	}
	fileSize, err := util.GetFileSize(tarFilePath)
	if err != nil {
		log.Errorf("tar dir %s failed, err %v", tmpPath, err)
		return
	}
	log.Infof("tar success. dir %s result file: %s size: %d (%s)",
		tmpPath, tarFilePath, fileSize, util.HumanSize(fileSize))

}

// MongoDumpHelper 逻辑备份
type MongoDumpHelper struct {
	MongoHost    *mymongo.MongoHost
	MongoDumpBin string
	User         string
	Pass         string
	AuthDb       string
	OsUser       string // 程序是以root跑的，会su到osUser去执行命令。能否直接用osUser执行？
}

// NewMongoDumpHelper 逻辑备份
func NewMongoDumpHelper(mongoHost *mymongo.MongoHost, dumpBin, user, pass, authDb string, osUser string) *MongoDumpHelper {
	return &MongoDumpHelper{
		MongoHost:    mongoHost,
		MongoDumpBin: dumpBin,
		User:         user,
		Pass:         pass,
		AuthDb:       authDb,
		OsUser:       osUser,
	}
}

// LogicalDumpPartial  逻辑备份 指定库表
// 有3种情况:
// 1. 备份一个表 : -c tableName
// 2. 备份多个表 :  --excludeCollection tableName1 --excludeCollection tableName2 ...

// LogicalDumpPartial  逻辑备份 指定库表
// 有3种情况:
// 1. 备份一个表 : -c tableName
// 2. 备份多个表 :  --excludeCollection tableName1 --excludeCollection tableName2 ...

// DumpPartial  逻辑备份 指定库表
func (m *MongoDumpHelper) DumpPartial(outDir string, logFileName string, filter *NsFilter) (cmdLineList []string, cmdLine string, err error) {
	// 如果filter为nil，请使用LogicalDumpAll
	if filter == nil {
		panic("filter is nil")
	}
	fmt.Printf("debug DumpPartial filter: %+v\n", filter)
	dbColList, err := GetDbCollectionWithFilter(m.MongoHost.Host, m.MongoHost.Port, m.User, m.Pass, m.AuthDb, filter)
	if err != nil {
		err = errors.Wrap(err, "GetDbCollectionWithFilter")
		return
	}
	if dbColList == nil {
		err = errors.New("no match database or collection")
		return
	}
	fmt.Printf("debug DumpPartial dbColList: %+v\n", dbColList)
	for _, dbRow := range dbColList {
		// 没有匹配的表，就不备份
		if len(dbRow.Col) == 0 {
			continue
		}
		if cmdLine, err = m.dumpDbCol(outDir, logFileName, dbRow.Db, dbRow.Col, dbRow.notMachCol); err != nil {
			return
		}
		cmdLineList = append(cmdLineList, cmdLine)
	}
	return
}

func (m *MongoDumpHelper) dumpDbCol(outDir string, logFileName string,
	dbName string, colList []string, excludeColList []string) (cmdLine string, err error) {
	dumpCmd := mycmd.New(m.MongoDumpBin, "-u", m.User,
		"-p", mycmd.Password(m.Pass),
		"--host", m.MongoHost.Host, "--port", m.MongoHost.Port,
		fmt.Sprintf("--authenticationDatabase=%s", m.AuthDb),
		"-d", dbName)

	if len(colList) == 1 {
		dumpCmd.Append("--collection", colList[0])
	} else if len(excludeColList) > 0 {
		for _, col := range excludeColList {
			dumpCmd.Append("--excludeCollection", col)
		}
	}

	dumpCmd.Append(
		"-o", outDir, ">", path.Join(outDir, logFileName), "2>&1",
	)
	_, _, _, err = dumpCmd.RunByBash(m.OsUser, time.Hour*24)
	return dumpCmd.GetCmdLine(m.OsUser, true), err
}

// LogicalDumpAll  全量逻辑备份
func (m *MongoDumpHelper) LogicalDumpAll(outDir string, logFileName string) (cmdLine string, err error) {
	//
	dumpCmd := mycmd.New(m.MongoDumpBin, "-u", m.User, "-p", mycmd.Password(m.Pass),
		"--host", m.MongoHost.Host, "--port", m.MongoHost.Port,
		fmt.Sprintf("--authenticationDatabase=%s", m.AuthDb),
		"-o", outDir, ">", path.Join(outDir, logFileName), "2>&1")
	_, _, _, err = dumpCmd.RunByBash(m.OsUser, time.Hour*24)
	return dumpCmd.GetCmdLine(m.OsUser, true), errors.Wrap(err, "LogicalDump")
}

// RemoveAdminDir  全量逻辑备份
func (m *MongoDumpHelper) RemoveAdminDir(tmpPath string) (err error) {
	adminDir := path.Join(tmpPath, "admin")
	if util.FileExists(adminDir) {
		return os.RemoveAll(adminDir)
	} else {
		return errors.New("admin Dir not exists, path=" + adminDir)
	}

}

// Tar 打包
func (m *MongoDumpHelper) Tar(dumpPath string, zip bool, delDumpPath bool) (tarPath string, err error) {
	dumpDirName := path.Base(dumpPath)
	var tarArg, tarFile string
	if zip {
		tarArg = "zcvf"
		tarFile = fmt.Sprintf("%s.tar.gz", dumpDirName)
		tarPath = path.Join(path.Dir(dumpPath), tarFile)
	} else {
		tarArg = "cvf"
		tarFile = fmt.Sprintf("%s.tar", dumpDirName)
		tarPath = path.Join(path.Dir(dumpPath), tarFile)
	}
	tarCmd := mycmd.New("cd", path.Dir(tarPath), "&&", "tar", tarArg, tarFile, dumpDirName)
	_, _, _, err = tarCmd.RunByBash("", time.Hour*24)
	if err != nil {
		return "", errors.Wrap(err, tarCmd.GetCmdLine("", true))
	}

	if delDumpPath {
		err = os.RemoveAll(dumpPath)
		if err != nil {
			err = errors.Wrap(err, "remove dumpPath")
			return
		}
	}

	return
}
