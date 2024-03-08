package pitr

import (
	"bufio"
	"bytes"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/util"
	"fmt"
	"os"
	"os/exec"
	"path"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

const BackupTypeManual = "MANUAL" // 按需做的备份
const BackupTypeFull = "FULL"
const BackupTypeAuto = "AUTO"
const BackupTypeIncr = "INCR"
const BackupTypeAll = "ALL"
const MongoVersionUnknown = "0"
const MongoVersionV24 = "2.4"
const MongoVersionV30 = "3.0"
const MongoVersionV32 = "3.2"
const MongoVersionV34 = "3.4"
const MongoVersionV36 = "3.6"
const MongoVersionV40 = "4.0"
const MongoVersionV42 = "4.2"
const MongoVersionV44 = "4.4"
const MongoVersionV46 = "4.6"
const MongoVersionV100 = "100.7"

const cmdMaxTimeout = time.Hour * 7 * 24

// TS MongoDB Timestamp
type TS struct {
	Sec uint32 `bson:"Sec" json:"Sec,omitempty"`
	I   uint32 `bson:"I" json:"I,omitempty"`
}

// JsonV1 mongodump’s Extended JSON v1
func (ts *TS) JsonV1() string {
	return fmt.Sprintf(`Timestamp(%d,%d)`, ts.Sec, ts.I)
}

// JsonV2 mongodump’s Extended JSON v2
func (ts *TS) JsonV2() string {
	return fmt.Sprintf(`{"$timestamp":{"t":%d,"i":%d}}`, ts.Sec, ts.I)
}

// BackupResult 备份结果
type BackupResult struct {
	BackupFileName *BackupFileName `bson:"BackupFileName" json:"BackupFileName"`
	BackupType     string          `bson:"BackupType" json:"BackupType"`
	FullName       string          `bson:"fullName" json:"fullName"` // 所属的FullName
	IncrSeq        uint32          `bson:"IncrSeq" json:"IncrSeq"`
	Start          time.Time       `bson:"Start" json:"Start,omitempty"`
	End            time.Time       `bson:"End" json:"End,omitempty"`
	FirstTs        TS              `bson:"FirstTs" json:"FirstTs"`
	LastTs         TS              `bson:"LastTs" json:"LastTs"`
	FilePath       string          `bson:"FilePath" json:"FilePath"`
	FileSize       int64           `bson:"FileSize" json:"FileSize"`
}

// ConvertFileNameTimeStringToUnixTime as func name TODO: 是否需要考虑时区
func ConvertFileNameTimeStringToUnixTime(sec string) (uint32, error) {
	loc, err := time.LoadLocation("Asia/Chongqing")
	if err != nil {
		return 0, fmt.Errorf("Get Asia/Chongqing tz failed %v", err)
	}

	var vv uint32

	if tv, err := time.ParseInLocation("20060102150405", sec, loc); err != nil {
		return 0, fmt.Errorf("bad format: sec:%v", err)
	} else {
		vv = uint32(tv.Unix())
	}

	return vv, nil
}

// ConvertFileNameTimeStringToTs as func name
func ConvertFileNameTimeStringToTs(sec, i string) (*TS, error) {
	ts := new(TS)
	if vv, err := ConvertFileNameTimeStringToUnixTime(sec); err != nil {
		return nil, fmt.Errorf("bad format: Sec:%v", err)
	} else {
		ts.Sec = vv
	}
	if vv, err := strconv.ParseUint(i, 10, 32); err != nil {
		return nil, fmt.Errorf("bad format: I:%v", err)
	} else {
		ts.I = uint32(vv)
	}
	return ts, nil
}

/*
ParseTs 在log中找到firstTS和lastTS
2019-12-17T18:01:40.883+0800	firstTS=(1576576891 1)
2019-12-17T18:01:40.883+0800	lastTS=(1576576892 3)
*/
func ParseTs(buffer bytes.Buffer) (*TS, *TS, error) {
	var m1 = regexp.MustCompile(`(first|last)TS=\((\d+)\s+(\d+)\)$`)
	var firstTS, lastTS TS
	scanner := bufio.NewScanner(&buffer)
	for scanner.Scan() {
		line := scanner.Bytes()
		if matchRows := m1.FindSubmatch(line); matchRows != nil {
			log.Printf("read firstTS: %s match %s", line, matchRows)
			var u1, u2 uint64
			if u64, err := strconv.ParseUint(string(matchRows[2]), 10, 32); err == nil {
				u1 = u64
			}
			if u64, err := strconv.ParseUint(string(matchRows[3]), 10, 32); err == nil {
				u2 = u64
			}
			if string(matchRows[1]) == "first" {
				firstTS.Sec = uint32(u1)
				firstTS.I = uint32(u2)
			} else if string(matchRows[1]) == "last" {
				lastTS.Sec = uint32(u1)
				lastTS.I = uint32(u2)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, nil, err
	}
	return &firstTS, &lastTS, nil
}

// MakeTmpdir make tmp dir
func MakeTmpdir(dir string, backup_type string) (string, error) {
	currentTime := time.Now().Unix()
	dirName := fmt.Sprintf("mongodump-%s-%d", backup_type, currentTime)
	tmpdir := path.Join(dir, dirName)
	log.Debugf("dirname:%s", tmpdir)

	if err := os.Mkdir(tmpdir, os.FileMode(0755)); err == nil {
		return tmpdir, nil
	} else {
		return "", err
	}
}

// DoCommand as func name
func DoCommand(bin string, args ...string) (bytes.Buffer, bytes.Buffer, error) {
	cmd := exec.Command(bin, args...)
	var outb, errb bytes.Buffer
	cmd.Stdout = &outb
	cmd.Stderr = &errb
	err := cmd.Run()
	return outb, errb, err
}

// ExecResult as func name
type ExecResult struct {
	Start   time.Time
	End     time.Time
	Cmdline string
	Stdout  bytes.Buffer
	Stderr  bytes.Buffer
}

// DoCommandV2 as func name
func DoCommandV2(bin string, args ...string) (*ExecResult, error) {
	var ret = ExecResult{}
	ret.Start = time.Now()
	cmd := exec.Command(bin, args...)
	cmd.Stdout = &ret.Stdout
	cmd.Stderr = &ret.Stderr
	err := cmd.Run()
	ret.End = time.Now()
	ret.Cmdline = fmt.Sprintf("%s %s", bin, strings.Join(args, " "))
	return &ret, err
}

// GetVersion Get mongo version by mongo shell
func GetVersion(conn *mymongo.MongoHost) (*mymongo.MongoVersion, error) {
	bin := "mongo"
	var args []string
	args = append(args, "--quiet", fmt.Sprintf("%s:%s/admin", conn.Host, conn.Port),
		"--eval", "db.version()")
	// commandLine := fmt.Sprintf("%s %s", bin, strings.Join(args, " "))
	// log.Printf("Exec commandLine:%s", commandLine)
	outBuf, errBuf, err := DoCommand(bin, args...)
	if err != nil {
		return nil, fmt.Errorf("exec %s failed:%s", bin, errBuf.String())
	}
	version := strings.TrimSpace(outBuf.String())
	return mymongo.ParseMongoVersion(version)
}

// DoBackup 执行备份
func DoBackup(connInfo *mymongo.MongoHost, backupType, dir string, zip bool,
	lastBackup *BackupFileName, maxTs *TS) (*BackupFileName, error) {
	dbConn, err := connInfo.Connect()
	if err != nil {
		return nil, errors.Wrap(err, "conn")
	}
	defer dbConn.Disconnect(nil)

	//upsert一行数据到admin.gcs.backup表中，让备份中oplog至少有一条数据，允许Insert失败.
	mymongo.InsertBackupHeartbeat(dbConn, *connInfo, backupType, dir)

	var isMasterOut mymongo.IsMasterResult
	err = mymongo.RunCommand(dbConn, "admin", "isMaster", 10, &isMasterOut)
	if err != nil {
		return nil, err
	} else if isMasterOut.Primary == "" {
		log.Printf("Get primary err:%v", err)
		return nil, fmt.Errorf("Get primary err:%v", err)
	}

	if backupType == BackupTypeFull {
		return DoBackupFull(connInfo, backupType, dir, zip, lastBackup)
	} else if backupType == BackupTypeIncr {
		return DoBackupIncr(connInfo, backupType, dir, zip, lastBackup, maxTs)
	} else {
		return nil, errors.Errorf("bad backupType: %s", backupType)
	}
}

// GetMongoDumpBin 根据版本号获取mongodump的二进制文件名
// 2.x : 不支持
// 3.x, 4.0, 4.2: mongodump.$v0.$v1
// others: mongodump.100
func GetMongoDumpBin(version *mymongo.MongoVersion) (bin string, err error) {
	if version == nil {
		return "", errors.New("version is nil")
	}

	switch version.Major {
	case 2:
		return "", fmt.Errorf("not support version:%s", version.Version)
	case 3:
		bin = fmt.Sprintf("mongodump.%d.%d", version.Major, version.Minor)
	case 4:
		switch version.Minor {
		case 0, 2:
			bin = fmt.Sprintf("mongodump.%d.%d", version.Major, version.Minor)
		default:
			bin = fmt.Sprintf("mongodump.%s", MongoVersionV100) // >=4.4 100.7
		}
	default:
		bin = fmt.Sprintf("mongodump.%s", MongoVersionV100) // 100.7
	}

	// Executable returns the path name for the executable that started the current process.
	ex, err := os.Executable()
	if err != nil {
		return
	}
	bin = path.Join(path.Dir(ex), "mongotools", bin)
	return
}

// DoBackupFull 执行全量备份
func DoBackupFull(connInfo *mymongo.MongoHost, backupType, dir string, zip bool, lastBackup *BackupFileName) (*BackupFileName, error) {
	dumpCmd, err := buildDumpFullCmd(connInfo, zip, lastBackup, nil)
	if err != nil {
		return nil, err
	}

	workdir, err := MakeTmpdir(dir, backupType)
	if err != nil {
		log.Fatalf("make_tmpdir failed %v", err)

	}
	if err := os.Chdir(workdir); err != nil {
		log.Fatalf("Cannot chdir to %s", workdir)
	}

	startTime := time.Now()
	exitCode, stdout, stderr, err := dumpCmd.Run(cmdMaxTimeout)
	endTime := time.Now()
	dumpLogFilePath := "dump.log"
	saveLog(dumpCmd.GetCmdLine("", true), dumpLogFilePath, stdout, stderr, err)

	errBuf := bytes.NewBufferString(stderr)
	firstTs, lastTs, _ := ParseTs(*errBuf)
	log.Debugf("return %v %v", firstTs, lastTs)
	if exitCode != 0 || err != nil {
		log.Warnf("Exec Command %s return Error: %v stdout %s stderr %s",
			dumpCmd.GetCmdLine("", false), err, stdout, stderr)
		return nil, err
	}

	//    $output_dir = "mongodump-$name-INCR-$nodeip-$port-$endoplog-$ts-i";
	fNameObj, err := MakeFileName(BackupFileVersionV0, connInfo, backupType, startTime, endTime, firstTs, lastTs, "", 0)
	if err != nil {
		return nil, errors.Wrap(err, "MakeFileName")
	}
	outputDirname, err := fNameObj.GetFileUniqName()
	if err != nil {
		return nil, errors.Wrap(err, "MakeFileName")
	}

	log.Infof("MakeFileName return %s", outputDirname)

	//chdir to *dir && do do tar czvf
	if err := os.Chdir(dir); err != nil {
		log.Fatalf("Cannot chdir to %s", dir)
	}
	cwd, _ := os.Getwd()
	//	2019-12-17T18:01:40.883+0800	firstTS=(1576576891 1)
	//	2019-12-17T18:01:40.883+0800	lastTS=(1576576891 1)
	if exitCode, o, e, err := mycmd.NewCmdBuilder().Append("mv", workdir, outputDirname).
		Run(cmdMaxTimeout); exitCode != 0 || err != nil {
		log.Fatalf("chdir %s, Rename %s %s, o: %s, e: %s err: %v", cwd, workdir, outputDirname, o, e, err)
	}

	// $output_dir = "mongodump-$name-FULL-$nodeip-$port-$ymdh-$suffix";

	var tarBin, tarArg, tarSuffix = "tar", "cf", "tar"
	if !zip {
		tarBin, tarArg, tarSuffix = "tar", "czf", "tar.gz"
	}

	fNameObj.SetSuffix(fmt.Sprintf(".%s", tarSuffix))
	tarFile := strings.Join([]string{outputDirname, tarSuffix}, ".")
	tarCmd := mycmd.NewCmdBuilder().Append(tarBin, tarArg, tarFile, outputDirname)
	_, _, _, err = tarCmd.Run(cmdMaxTimeout)
	if err != nil {
		log.Warnf("DoCommand %s return err %v", tarCmd.GetCmdLine("", true), err)
	} else {
		log.Infof("DoCommand Succ: %s", tarCmd.GetCmdLine("", true))
	}
	if err = os.RemoveAll(outputDirname); err != nil {
		log.Printf("RemoveAll %s  error", outputDirname)
	} else {
		log.Printf("RemoveAll %s  succ", outputDirname)
	}
	fNameObj.FileName = tarFile
	fNameObj.Dir = dir
	fNameObj.FileSize, _ = util.GetFileSize(tarFile)
	return fNameObj, err
}

// DoBackupIncr 执行增量备份
func DoBackupIncr(connInfo *mymongo.MongoHost, backupType, dir string, zip bool,
	lastBackup *BackupFileName, maxTs *TS) (*BackupFileName, error) {
	log.Debugf("DoBackupIncr %v %v %v %v %+v", connInfo, backupType, dir, zip, lastBackup)
	if lastBackup == nil {
		return nil, errors.New("lastBackup is nil")
	}

	dumpCmd, err := buildDumpIncrCmd(connInfo, zip, lastBackup, maxTs)
	if err != nil {
		return nil, err
	}

	workdir, err := MakeTmpdir(dir, backupType)
	if err != nil {
		log.Fatalf("make_tmpdir failed %v", err)

	}
	if err := os.Chdir(workdir); err != nil {
		log.Fatalf("Cannot chdir to %s", workdir)
	}

	startTime := time.Now()
	exitCode, stdout, stderr, err := dumpCmd.Run(cmdMaxTimeout)
	endTime := time.Now()
	dumpLogFilePath := "dump.log"
	saveLog(dumpCmd.GetCmdLine("", true), dumpLogFilePath, stdout, stderr, err)
	errb := bytes.NewBufferString(stderr)
	firstTs, lastTs, _ := ParseTs(*errb)
	log.Debugf("return %v %v", firstTs, lastTs)
	if exitCode != 0 || err != nil {
		log.Warnf("Exec Command %s return Error: %v stdout %s stderr %s",
			dumpCmd.GetCmdLine("", false), err, stdout, stderr)
		return nil, err
	}
	//chdir to *dir && do do tar czvf
	if err := os.Chdir(dir); err != nil {
		log.Fatalf("Cannot chdir to %s", dir)
	}

	//    $output_dir = "mongodump-$name-INCR-$nodeip-$port-$endoplog-$ts-i";
	fullStr, _ := lastBackup.GetV0FullStr()
	fNameObj, err := MakeFileName(BackupFileVersionV0, connInfo, backupType, startTime, endTime,
		firstTs, lastTs, fullStr, lastBackup.V0IncrSeq+1)
	if err != nil {
		return nil, errors.Wrap(err, "MakeFileName")
	}
	outputDirname, err := fNameObj.GetFileUniqName()
	if err != nil {
		return nil, errors.Wrap(err, "MakeFileName")
	}

	log.Infof("MakeFileName return %s", outputDirname)

	originFile := path.Join(workdir, "dump/local/oplog.rs.bson")
	oplogFile := outputDirname + "-oplog.rs.bson"
	if zip {
		originFile = originFile + ".gz"
		oplogFile = oplogFile + ".gz"
		fNameObj.SetSuffix("-oplog.rs.bson.gz")
	} else {
		fNameObj.SetSuffix("-oplog.rs.bson")
	}
	log.Debugf("DoCommand %s %s %s", "mv", originFile, oplogFile)

	mvCmd := mycmd.New("mv", originFile, oplogFile)
	if exitCode, _, stderr, err := mvCmd.Run(cmdMaxTimeout); exitCode != 0 || err != nil {
		log.Fatalf("DoCommand Failed. cmd:%v stderr %s err %s", mvCmd.GetCmdLine("", false), stderr, err)
	}

	if err := os.RemoveAll(workdir); err != nil {
		log.Printf("RemoveAll %s error", workdir)
	} else {
		log.Printf("RemoveAll %s succ", workdir)
	}

	fNameObj.FileName = oplogFile
	fNameObj.Dir = dir
	fNameObj.FileSize, _ = util.GetFileSize(oplogFile)
	return fNameObj, nil
}

func buildDumpIncrCmd(connInfo *mymongo.MongoHost, zip bool, lastBackup *BackupFileName, maxTs *TS) (*mycmd.CmdBuilder, error) {
	version, err := GetVersion(connInfo)
	if err != nil {
		return nil, errors.Wrap(err, "get version")
	}

	mongoDumpBin, err := GetMongoDumpBin(version)
	if err != nil {
		return nil, errors.Wrap(err, "get version")
	}
	dumpCmd := mycmd.NewCmdBuilder().Append(mongoDumpBin).
		Append("--host", connInfo.Host, "--port", connInfo.Port, "--authenticationDatabase", connInfo.AuthDb)

	if len(connInfo.User) > 0 {
		dumpCmd.Append("-u", connInfo.User)
	}
	if len(connInfo.Pass) > 0 {
		dumpCmd.Append("-p").AppendPassword(connInfo.Pass)
	}
	if zip {
		dumpCmd.Append("--gzip")
	}
	dumpCmd.Append("-d", "local", "-c", "oplog.rs")
	if maxTs != nil {
		if strings.Contains(path.Base(mongoDumpBin), MongoVersionV100) {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s,"$lte":%s}}`, lastBackup.LastTs.JsonV2(), maxTs.JsonV2()))
		} else {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s,"$lte":%s}}`, lastBackup.LastTs.JsonV2(), maxTs.JsonV2()))
		}
	} else {
		if strings.Contains(path.Base(mongoDumpBin), MongoVersionV100) {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s}}`, lastBackup.LastTs.JsonV2()))
		} else {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s}}`, lastBackup.LastTs.JsonV1()))
		}
	}

	return dumpCmd, nil
}

func buildDumpFullCmd(connInfo *mymongo.MongoHost, zip bool, lastBackup *BackupFileName, maxTs *TS) (*mycmd.CmdBuilder, error) {
	// ./mongotools/mongodump.2.4  mongodump.3.0  mongodump.3.2  mongodump.3.4  mongodump.3.6  mongodump.4.0  mongodump.4.2
	version, err := GetVersion(connInfo)
	if err != nil {
		return nil, errors.Wrap(err, "get version")
	}
	log.Infof("Get Version %v err %v", version, err)

	mongoDumpBin, err := GetMongoDumpBin(version)
	if err != nil {
		return nil, errors.Wrap(err, "get version")
	}

	if _, err := os.Stat(mongoDumpBin); os.IsNotExist(err) {
		return nil, errors.Wrap(err, "get mongoDumpBin")
	}

	dumpCmd := mycmd.NewCmdBuilder().Append(mongoDumpBin).
		Append("--host", connInfo.Host, "--port", connInfo.Port, "--authenticationDatabase", connInfo.AuthDb)

	if len(connInfo.User) > 0 {
		dumpCmd.Append("-u", connInfo.User)
	}
	if len(connInfo.Pass) > 0 {
		dumpCmd.Append("-p").AppendPassword(connInfo.Pass)
	}
	if zip {
		dumpCmd.Append("--gzip")
	}
	dumpCmd.Append("--oplog")
	return dumpCmd, nil
}
