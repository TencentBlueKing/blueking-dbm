package logical

import (
	"bufio"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/toolkit/pitr"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

// RestoreArgs restore args
type RestoreArgs struct {
	IsPartial   bool `json:"isPartial"` // 为true时，只恢复指定库和表
	Oplog       bool `json:"oplog"`
	PartialArgs struct {
		DbList        []string `json:"dbList"`
		IgnoreDbList  []string `json:"ignoreDbList"`
		ColList       []string `json:"colList"`
		IgnoreColList []string `json:"ignoreColList"`
	} `json:"partialArgs"`
}

// RestoreOption logical backup and restore
type RestoreOption struct {
	RestoreExePath string
	RestoreFile    string
	MongoHost      *mymongo.MongoHost
	BackupType     string
	Dir            string
	Zip            bool
	DryRun         bool
	Args           *RestoreArgs
}

// Restore Do Restore
func Restore(option *RestoreOption) {
	log.Infof("start logical restore, option: %+v", option)
	helper := NewMongoRestoreHelper(option.MongoHost, option.RestoreExePath,
		option.MongoHost.User, option.MongoHost.Pass, option.MongoHost.AuthDb, "")

	// checkDstMongo
	filter := NewNsFilter(option.Args.PartialArgs.DbList, option.Args.PartialArgs.IgnoreDbList,
		option.Args.PartialArgs.ColList, option.Args.PartialArgs.IgnoreColList)

	if option.Args.IsPartial {
		host := option.MongoHost
		dbColList, err := GetDbCollectionWithFilter(host.Host, host.Port, host.User, host.Pass, host.AuthDb, filter)
		if err != nil {
			log.Errorf("GetDbCollectionWithFilter failed %v", err)
			return
		}
		if len(dbColList) >= 0 {
			for _, row := range dbColList {
				log.Errorf("some db or col already exists, db:%s col:%+v", row.Db, row.Col)
			}
			return
		}
	}

	dstDir, err := UntarFile(option.RestoreFile)
	if err != nil {
		log.Errorf("UntarFile failed %v", err)
		return
	}

	// 删除掉admin dir，这个目录不需要
	adminDir := path.Join(dstDir, "admin")
	if fileExists(adminDir) {
		err = os.RemoveAll(adminDir)
		if err != nil {
			log.Errorf("Remove %s failed %v", adminDir, err)
		}
	}

	// 部分恢复 这里要删除掉不需要的库和表文件.
	if option.Args.IsPartial {
		leftDbCol, err := RemoveFileNotInFilter(dstDir, filter)
		if err != nil {
			log.Errorf("RemoveFileNotInFilter failed %v", err)
			return
		}
		if len(leftDbCol) == 0 {
			log.Errorf("Partial Restore, no db and collection matched")
			return
		}
	}

	restoreLog, err := helper.Restore(dstDir, dstDir, option.Args.Oplog)
	if err != nil {
		log.Errorf("restore error: %s", err)
		return
	}

	restoreSucc, restoreFailed, restoreErr := CheckRestoreLog(restoreLog)
	if restoreErr != nil {
		log.Errorf("CheckRestoreLog error: %s", restoreErr)
		return
	}
	if restoreFailed > 0 {
		log.Errorf("%d document restore succ, %d document restore failed", restoreSucc, restoreFailed)
		return
	}
	if err := os.RemoveAll(dstDir); err != nil {
		log.Errorf("remove %s failed %v", dstDir, err)
	}
	log.Infof("%d document restore succ, %d document restore failed", restoreSucc, restoreFailed)

}

// MongoRestoreHelper mongorestore helper
type MongoRestoreHelper struct {
	MongoHost *mymongo.MongoHost
	Bin       string
	User      string
	Pass      string
	AuthDb    string
	OsUser    string // 程序是以root跑的，会su到osUser去执行命令。能否直接用osUser执行？
}

// NewMongoRestoreHelper new
func NewMongoRestoreHelper(mongoHost *mymongo.MongoHost, restoreBin, user, pass, authDb string, osUser string) *MongoRestoreHelper {
	return &MongoRestoreHelper{
		MongoHost: mongoHost,
		Bin:       restoreBin,
		User:      user,
		Pass:      pass,
		AuthDb:    authDb,
		OsUser:    osUser,
	}
}

// Restore do mongorestore
// todo save log to file
func (m MongoRestoreHelper) Restore(dstDir string, logDir string, oplog bool) (restoreLog string, err error) {
	logFileName := "restore.log"
	restoreLog = path.Join(logDir, logFileName)
	restoreCmd := mycmd.New(m.Bin, "-u", m.User, "-p").
		AppendPassword(m.Pass).
		Append("--host", m.MongoHost.Host, "--port", m.MongoHost.Port,
			fmt.Sprintf("--authenticationDatabase=%s", m.AuthDb),
			"--stopOnError",
			"--dir", dstDir)
	if oplog {
		restoreCmd.Append("--oplogReplay")
	}

	outFile, err := os.Create(restoreLog)
	if err != nil {
		return "", errors.Wrap(err, fmt.Sprintf("create %s failed", restoreLog))
	}
	defer outFile.Close()
	_, err = restoreCmd.Run3(time.Hour*24, outFile, outFile)
	if err != nil {
		err = errors.Wrap(err, restoreCmd.GetCmdLine("", true))
		return
	}

	return
}

/*
CheckRestoreLog 分析restoreLog . 得到恢复的库和表
2023-10-16T11:37:47.821+0800	preparing collections to restore from
2023-10-16T11:37:47.821+0800 finished restoring cyc1.tb1 (0 documents, 3 failures)
2023-10-16T11:37:47.821+0800 continuing through error: E11000 duplicate key error collection:...
2023-10-16T11:37:47.938+0800    0 document(s) restored successfully. 6 document(s) failed to restore.
*/
func CheckRestoreLog(logFile string) (restoreSucc, restoreFail int, err error) {
	restoreSucc = -1
	restoreFail = -1

	file, err := os.Open(logFile)
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	isFirst := true
	firstLineContains := "preparing collections to restore from" // 第一行必须包含这个.
	line := ""

	// optionally, resize scanner's capacity for lines over 64K, see next example
	for scanner.Scan() {
		line = scanner.Text()
		fs := strings.SplitN(line, "\t", 2)
		if len(fs) != 2 {
			err = fmt.Errorf("invalid log line %s", line)
			return
		}
		line = fs[1]
		if isFirst {
			if !strings.Contains(line, firstLineContains) {
				err = fmt.Errorf("first line not contains %s", firstLineContains)
				return
			}
			isFirst = false
			continue
		}

		// finished restoring cyc1.tb1 (0 documents, 3 failures)
		if strings.HasSuffix(line, "finished restoring") {
			words := strings.Fields(line)
			if len(words) != 7 {
				err = fmt.Errorf("invalid log line %s", line)
				return
			}
			ns := words[2]
			succ := words[4]
			fail := words[6]
			fmt.Printf("restore %s succ %s fail %s\n", ns, succ, fail)
		}
	}

	if err = scanner.Err(); err != nil {
		return -1, -1, errors.Wrap(err, "read log file failed")
	}

	if strings.Contains(line, "restored successfully") {
		words := strings.Fields(line)
		if len(words) == 9 {
			var v int
			if v, err = strconv.Atoi(words[0]); err == nil {
				restoreSucc = v
			} else {
				err = fmt.Errorf("invalid log line %s", line)
				return
			}

			if v, err = strconv.Atoi(words[4]); err == nil {
				restoreFail = v
			} else {
				err = fmt.Errorf("invalid log line %s", line)
				return
			}
		}
	}

	if restoreSucc == -1 || restoreFail == -1 {
		err = fmt.Errorf("invalid last log line %s", line)
	}

	return
}

// UntarFile untar file to current dir
func UntarFile(resultFile string) (dstDir string, err error) {
	resultFilePath, err := filepath.Abs(resultFile)
	if err != nil {
		return
	}
	dirName := filepath.Dir(resultFilePath)

	// 备份目录
	tmpPath, _, err := getTmpSubDir(dirName, "restore")
	if err != nil {
		return
	}

	resultFileBase := filepath.Base(resultFile)
	var resultFileNoSuffix string

	untarCmd := mycmd.New()
	if strings.HasSuffix(resultFile, ".tar.gz") || strings.HasSuffix(resultFile, ".tgz") {
		untarCmd.Append("tar", "zxf", resultFile, "-C", tmpPath)
		resultFileNoSuffix = strings.TrimSuffix(resultFileBase, ".tgz")
		resultFileNoSuffix = strings.TrimSuffix(resultFileBase, ".tar.gz")
	} else if strings.HasSuffix(resultFile, ".tar") {
		untarCmd.Append("tar", "xf", resultFile, "-C", tmpPath)
		resultFileNoSuffix = strings.TrimSuffix(resultFileBase, ".tar")
	} else {
		isDir, _ := pitr.IsDirectory(resultFile)
		if isDir {
			dstDir = resultFile
			return
		} else {
			err = errors.New("invalid file type")
			return
		}
	}

	_, err = untarCmd.Run2(time.Hour * 24)
	if err != nil {
		err = fmt.Errorf("cmd:%s return err %v", untarCmd.GetCmdLine2(true), err)
		return
	}

	dstDir = filepath.Join(tmpPath, resultFileNoSuffix)
	return
}

/*
GetDbCollectionFromDir get db and collection from dir

	dump/xxx/xxx.bson ok
	dump/xxx/xxx.metadata.json ski
	dump/xxx/xxx.bson.gz ok
	dump/xxx/xxx.metadata.json skip
	dump/xxx/others error
	dump/others ok
*/
func GetDbCollectionFromDir(dirName string) ([]DbCollection, error) {
	var dbCollections []DbCollection
	var err error

	files, err := os.ReadDir(dirName)
	if err != nil {
		return nil, err
	}

	for _, file := range files {
		if !file.IsDir() {
			continue
		}
		var dbCollection DbCollection
		dbCollection.Db = file.Name()
		subFiles, err := os.ReadDir(path.Join(dirName, file.Name()))
		if err != nil {
			return nil, err
		}
		for _, subFile := range subFiles {
			if subFile.IsDir() {
				return nil, errors.Errorf("invalid dir structure %s", path.Join(dirName, file.Name(), subFile.Name()))
			}
			if strings.HasSuffix(subFile.Name(), ".metadata.json") {
				continue
			} else if strings.HasSuffix(subFile.Name(), ".bson") {
				dbCollection.Col = append(dbCollection.Col, strings.TrimSuffix(subFile.Name(), ".bson"))
			} else if strings.HasSuffix(subFile.Name(), ".bson.gz") {
				dbCollection.Col = append(dbCollection.Col, strings.TrimSuffix(subFile.Name(), ".bson.gz"))
			} else {
				return nil, errors.Errorf("invalid file %s", path.Join(dirName, file.Name(), subFile.Name()))
			}
		}
	}

	return dbCollections, nil
}

// RemoveFileNotInFilter remove file if not in filter's match list
func RemoveFileNotInFilter(dirName string, filter *NsFilter) ([]DbCollection, error) {
	dbRows, err := GetDbCollectionFromDir(dirName)
	if err != nil {
		return nil, err
	}
	var left []DbCollection
	for _, row := range dbRows {
		if !filter.IsDbMatched(row.Db) {
			err = os.RemoveAll(path.Join(dirName, row.Db))
			if err != nil {
				return nil, err
			}
			continue
		}

		matchList, notMatchList := filter.FilterTb(row.Col)
		if len(matchList) == 0 {
			err = os.RemoveAll(path.Join(dirName, row.Db))
			if err != nil {
				return nil, err
			}
			continue
		}

		for _, col := range notMatchList {
			var toDelFileList = []string{}
			toDelFileList = append(toDelFileList,
				fmt.Sprintf("%s/%s/%s.bson", dirName, row.Db, col),
				fmt.Sprintf("%s/%s/%s.bson.gz", dirName, row.Db, col),
				fmt.Sprintf("%s/%s/%s.metadata.json", dirName, row.Db, col),
			)
			for _, file := range toDelFileList {
				if !fileExists(file) {
					continue
				}
				err = os.Remove(file)
				if err != nil {
					return nil, err
				}
			}
		}
		var newRow DbCollection
		newRow.Db = row.Db
		newRow.Col = matchList
		left = append(left, row)
	}
	return left, nil
}

/*2023-10-17T18:24:00.300+0800    writing cyc1.tb2 to dump/mongodump-1697538239/cyc1/tb2.bson
2023-10-17T18:24:00.310+0800    writing cyc1.x to dump/mongodump-1697538239/cyc1/x.bson
2023-10-17T18:24:00.343+0800    done dumping cyc1.tb2 (1 document)
2023-10-17T18:24:00.343+0800    done dumping cyc1.x (1 document)
*/

// checkDumpLog check dump log
func checkDumpLog(dumpLog string) (map[string]int, error) {
	var colStart, colEnd int
	ns := make(map[string]int)
	file, err := os.Open(dumpLog)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	line := ""

	// optionally, resize scanner's capacity for lines over 64K, see next example
	for scanner.Scan() {
		line = scanner.Text()
		fs := strings.SplitN(line, "\t", 2)
		if len(fs) != 2 {
			err = fmt.Errorf("invalid log line %s", line)
			return nil, err
		}
		line = fs[1]

		// writing cyc1.x to dump/mongodump-1697538239/cyc1/x.bson
		if strings.HasPrefix(line, "writing") {
			words := strings.Fields(line)
			if len(words) == 4 {
				nsName := words[1]
				ns[nsName] = 0
				colStart = 1
			} else {
				fmt.Printf("debug skip line %s\n", line)
			}

		} else if strings.HasPrefix(line, "done dumping") {
			// one dumping cyc1.x (1 document)
			words := strings.Fields(line)
			if len(words) == 5 {
				nsName := words[2]
				nDocument := strings.Replace(words[3], "(", "", 1)
				n, err := strconv.Atoi(nDocument)
				if err != nil {
					return nil, errors.Wrap(err, fmt.Sprintf("invalid log line %s", line))
				}
				ns[nsName] = n
				colEnd = 1
			} else {
				fmt.Printf("debug skip line %s\n", line)
			}

		}
	}

	if colStart != colEnd {
		return nil, fmt.Errorf("some collection not finished")
	}

	return ns, nil
}
