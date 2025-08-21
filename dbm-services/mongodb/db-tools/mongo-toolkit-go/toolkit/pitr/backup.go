package pitr

import (
	"bufio"
	"bytes"
	"context"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/util"
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

// JsonV1 mongodump's Extended JSON v1
func (ts *TS) JsonV1() string {
	return fmt.Sprintf(`Timestamp(%d,%d)`, ts.Sec, ts.I)
}

// JsonV2 mongodump's Extended JSON v2
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
		return 0, fmt.Errorf("get Asia/Chongqing tz failed %v", err)
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
func ParseTs(buffer *bytes.Buffer) (*TS, *TS, error) {
	var m1 = regexp.MustCompile(`(first|last)TS=\((\d+)\s+(\d+)\)$`)
	var firstTS, lastTS TS
	scanner := bufio.NewScanner(buffer)
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

	outBuf, errBuf, err := DoCommand(bin, args...)
	if err != nil {
		return nil, fmt.Errorf("exec %s failed, err: %s, errBuf: %s", bin, err, errBuf.String())
	}
	version := strings.TrimSpace(outBuf.String())
	return mymongo.ParseMongoVersion(version)
}

// DoBackup 执行备份
func DoBackup(connInfo *mymongo.MongoHost, backupType, dir string, zip bool,
	archive bool,
	lastBackup *BackupFileName, maxTs *TS, numParallelCollections int) (*BackupFileName, error) {
	dbConn, err := connInfo.Connect()
	if err != nil {
		return nil, errors.Wrap(err, "conn")
	}
	defer dbConn.Disconnect(context.TODO())

	//upsert一行数据到admin.gcs.backup表中，让备份中oplog至少有一条数据，允许Insert失败.
	// 没有权限。不写这条.
	// mymongo.InsertBackupHeartbeat(dbConn, *connInfo, backupType, dir)

	var isMasterOut mymongo.IsMasterResult
	err = mymongo.RunCommand(dbConn, "admin", "isMaster", 10, &isMasterOut)
	if err != nil {
		return nil, err
	} else if isMasterOut.Primary == "" {
		log.Printf("get primary err:%v", err)
		return nil, fmt.Errorf("get primary err:%v", err)
	}

	// 如果使用archive，则必须使用zip
	if archive {
		zip = true // 使用zstd压缩
	}

	switch backupType {
	case BackupTypeFull:
		return DoBackupFull(connInfo, backupType, dir, zip, archive, lastBackup, numParallelCollections)
	case BackupTypeIncr:
		return DoBackupIncr(connInfo, backupType, dir, zip, archive, lastBackup, maxTs)
	default:
		return nil, errors.Errorf("bad backupType: %s", backupType)
	}
}

// DoBackupFull 执行全量备份
func DoBackupFull(connInfo *mymongo.MongoHost, backupType, dir string, zip bool, archive bool,
	lastBackup *BackupFileName, numParallelCollections int) (*BackupFileName, error) {
	archiveFile := "dump.archive"
	dumpCmd, err := buildDumpFullCmd(connInfo, zip, archive, archiveFile, lastBackup, numParallelCollections)
	if err != nil {
		return nil, err
	}

	workdir, err := MakeTmpdir(dir, backupType)
	if err != nil {
		log.Fatalf("make tmpdir failed, err: %v", err)
	}
	if err := os.Chdir(workdir); err != nil {
		log.Fatalf("chdir to %s failed, err: %v", workdir, err)
	}

	dumpLogFilePath := "dump.log"
	var cmdList []*mycmd.MyExec
	exec1, err := mycmd.NewMyExec(dumpCmd, cmdMaxTimeout, nil, dumpLogFilePath, false)
	if err != nil {
		return nil, err
	}
	defer exec1.CancelFunc()
	cmdList = append(cmdList, exec1)

	if archive && zip {
		exec2, err := mycmd.NewMyExec(
			mycmd.New(MustFindBinPath("zstd", consts.GetDbTool("mongotools")), "-", "-o", archiveFile),
			cmdMaxTimeout, nil, os.DevNull, false)
		if err != nil {
			return nil, err
		}
		defer exec2.CancelFunc()
		cmd1Output, err := exec1.ExecHandle.StdoutPipe()
		if err != nil {
			log.Fatalf("StdoutPipe failed: %v", err)
		}
		exec2.SetStdin(cmd1Output)
		cmdList = append(cmdList, exec2)
	}

	startTime := time.Now()
	for _, cmd := range cmdList {
		log.Infof("DoBackupFull cmd: %s", cmd.CmdBuilder.GetCmdLine("", true))
	}
	errorsList := runCmdList(cmdList)
	endTime := time.Now()
	if len(errorsList) > 0 {
		for _, err := range errorsList {
			log.Warnf("DoBackupFull error: %v", err)
			appendLog(dumpCmd.GetCmdLine("", true), dumpLogFilePath, "", "", err)
		}
		return nil, errors.Wrap(errorsList[0], "DoBackupFull")
	}

	stderr, err := os.ReadFile(dumpLogFilePath)
	if err != nil {
		log.Fatalf("read %s failed, err: %v", dumpLogFilePath, err)
	}

	for _, e := range cmdList {
		appendLog(e.CmdBuilder.GetCmdLine("", true), dumpLogFilePath, "", "", nil)
	}

	firstTs, lastTs, _ := ParseTs(bytes.NewBuffer(stderr))
	log.Debugf("return %v %v", firstTs, lastTs)
	//    $output_dir = "mongodump-$name-INCR-$nodeip-$port-$endoplog-$ts-i";
	fNameObj, err := MakeFileName(BackupFileVersionV0, connInfo, backupType, startTime, endTime, firstTs, lastTs, "", 0)

	if err != nil {
		return nil, errors.Wrap(err, "MakeFileName")
	}
	outputDirname, err := fNameObj.GetFileUniqName()
	if err != nil {
		return nil, errors.Wrap(err, "MakeFileName")
	}

	// 如果使用archive，则将dump.archive文件移动到outputDirname目录下.
	if archive {
		// now is in workdir
		if _, err := os.Stat(archiveFile); os.IsNotExist(err) {
			return nil, errors.Wrap(err, "get archiveFile")
		}
		fNameObj.FileName = outputDirname + ".archive"
		fNameObj.SetSuffix(".archive")
		// archive时, 不使用zip, 而是使用zstd
		if zip {
			fNameObj.FileName = fNameObj.FileName + ".zst"
			fNameObj.SetSuffix(".archive.zst")
		}
		log.Infof("archiveFile: %s", fNameObj.FileName)
		err = os.Rename(archiveFile, path.Join(dir, fNameObj.FileName))
		if err != nil {
			log.Fatalf("rename %s to %s failed, err: %v", archiveFile, fNameObj.FileName, err)
		}

		fNameObj.Dir = dir
		fNameObj.FileSize, _ = util.GetFileSize(path.Join(dir, fNameObj.FileName))

		// 将dump.log文件移动到outputDirname目录下.
		err = os.Rename(dumpLogFilePath, path.Join(dir, outputDirname+".dump.log"))
		if err != nil {
			log.Errorf("rename %s to %s failed, err: %v", archiveFile, fNameObj.FileName, err)
		}
		log.Infof("rename %s to %s succ", archiveFile, fNameObj.FileName)
		// delete workdir
		if err := os.Chdir(dir); err != nil {
			log.Fatalf("Cannot chdir to %s", dir)
		}

		// remove workdir if empty
		if err := os.Remove(workdir); err != nil {
			log.Printf("Remove %s error", workdir)
		} else {
			log.Printf("Remove %s succ", workdir)
		}

		return fNameObj, err
	} else {
		// 非archive时, 使用tar将dump目录打包
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
}

// DoBackupIncr 执行增量备份
func DoBackupIncr(connInfo *mymongo.MongoHost, backupType, dir string, zip bool, archive bool,
	lastBackup *BackupFileName, maxTs *TS) (*BackupFileName, error) {
	log.Debugf("DoBackupIncr %v %v %v %v %+v", connInfo, backupType, dir, zip, lastBackup)
	if lastBackup == nil {
		return nil, errors.New("lastBackup is nil")
	}

	dumpCmd, err := buildDumpIncrCmd(connInfo, zip, archive, lastBackup, maxTs)
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
	dumpLogFilePath := "dump.log"
	var cmdList []*mycmd.MyExec
	exec1, err := mycmd.NewMyExec(dumpCmd, cmdMaxTimeout, nil, dumpLogFilePath, false)
	if err != nil {
		return nil, err
	}
	defer exec1.CancelFunc()
	cmdList = append(cmdList, exec1)

	// var archiveFile string
	/*
		if archive && zip {
			zstdBin, err := GetZstdBin()
			if err != nil {
				return nil, err
			}
			archiveFile = "oplog.rs.bson.archive.zstd"
			exec2, err := mycmd.NewMyExec(mycmd.NewCmdBuilder().Append(zstdBin, "-", "-o", archiveFile),
				cmdMaxTimeout, nil, os.DevNull)
			if err != nil {
				return nil, err
			}
			defer exec2.CancelFunc()
			cmd1Output, err := exec1.ExecHandle.StdoutPipe()
			if err != nil {
				log.Fatalf("StdoutPipe failed: %v", err)
			}
			exec2.SetStdin(cmd1Output)
			cmdList = append(cmdList, exec2)
		}
	*/
	startTime := time.Now()
	log.Infof("DoBackupIncr cmd: %s cwd: %s", exec1.CmdBuilder.GetCmdLine("", true), workdir)
	errorsList := runCmdList(cmdList)
	endTime := time.Now()
	if len(errorsList) > 0 {
		for _, err := range errorsList {
			log.Warnf("DoBackupIncr error: %v", err)
			appendLog(dumpCmd.GetCmdLine("", true), dumpLogFilePath, "", "", err)
		}
		return nil, errors.Wrap(errorsList[0], "DoBackupIncr")
	}

	stderr, err := os.ReadFile(dumpLogFilePath)
	if err != nil {
		log.Fatalf("read %s failed, err: %v", dumpLogFilePath, err)
	}

	firstTs, lastTs, _ := ParseTs(bytes.NewBuffer(stderr))
	log.Debugf("return %v %v", firstTs, lastTs)

	appendLog(dumpCmd.GetCmdLine("", true), dumpLogFilePath, "", "", nil)

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

	/*
		3种情况:
		1. archive && zip
			originFile = "oplog.rs.bson.archive.zstd"
			oplogFile = outputDirname + "-oplog.rs.bson.archive.zstd"
			fNameObj.SetSuffix("-oplog.rs.bson.archive.zstd")
		2. !archive && zip
			originFile = "oplog.rs.bson"
			oplogFile = outputDirname + "-oplog.rs.bson.gz"
			fNameObj.SetSuffix("-oplog.rs.bson.gz")
		3. !archive && !zip
			originFile = "oplog.rs.bson"
			oplogFile = outputDirname + "-oplog.rs.bson"
			fNameObj.SetSuffix("-oplog.rs.bson")
	*/
	originFile := "dump/local/oplog.rs.bson"
	oplogFile := outputDirname + "-oplog.rs.bson"
	fNameObj.SetSuffix("-oplog.rs.bson")

	// 临时处理: archive模式时，使用zstd压缩.
	if archive {
		// doCommand 会使用zstd压缩.
		zstdCmd := mycmd.New(
			MustFindBinPath("zstd", consts.GetDbTool("mongotools")), "--rm", path.Join(workdir, originFile))
		log.Infof("DoCommand %s workdir: %s", zstdCmd.GetCmdLine("", true), workdir)
		exitCode, stdout, stderr, err := zstdCmd.Run(cmdMaxTimeout)
		if err != nil {
			log.Errorf("DoCommand %s workdir: %s return err %v stdout: %s stderr: %s exitCode: %d",
				zstdCmd.GetCmdLine("", true), workdir, err, stdout, stderr, exitCode)
			return nil, err
		}
		originFile = originFile + ".zst"
		oplogFile = oplogFile + ".zst"
		fNameObj.SetSuffix("-oplog.rs.bson.zst")
	} else if zip {
		originFile = originFile + ".gz"
		oplogFile = oplogFile + ".gz"
		fNameObj.SetSuffix("-oplog.rs.bson.gz")
	}
	originFilePath := path.Join(workdir, originFile)
	log.Debugf("DoCommand %s %s %s", "mv", originFilePath, oplogFile)
	err = os.Rename(originFilePath, oplogFile)
	if err != nil {
		log.Errorf("rename %s to %s failed, err: %v", originFilePath, oplogFile, err)
		return nil, errors.Wrap(err, "rename oplog.rs.bson")
	} else {
		log.Infof("rename %s to %s succ", originFile, oplogFile)
	}

	// 将dump.log文件移动到outputDirname目录下.
	dumpLogFile := path.Join(workdir, "dump.log")
	dumpLogFileNew := path.Join(dir, outputDirname+".dump.log")
	err = os.Rename(dumpLogFile, dumpLogFileNew)
	if err != nil {
		log.Errorf("rename %s to %s failed, err: %v", dumpLogFile, dumpLogFileNew, err)
	} else {
		log.Infof("rename %s to %s succ", dumpLogFile, dumpLogFileNew)
	}

	if err := os.RemoveAll(workdir); err != nil {
		log.Printf("RemoveAll %s error", workdir)
	} else {
		log.Printf("RemoveAll %s succ", workdir)
	}

	if err := os.Chdir(dir); err != nil {
		log.Fatalf("Cannot chdir to %s", dir)
	}

	fNameObj.FileName = oplogFile
	fNameObj.Dir = dir
	fNameObj.FileSize, _ = util.GetFileSize(oplogFile)
	return fNameObj, nil
}

// buildDumpIncrCmd 构建增量备份命令
// 参数:
//   - connInfo: 数据库连接信息
//   - zip: 是否使用zip压缩
//   - archive: 是否使用archive模式
//   - lastBackup: 上一次备份的文件名
//   - maxTs: 最大时间戳
func buildDumpIncrCmd(connInfo *mymongo.MongoHost, zip bool, archive bool, lastBackup *BackupFileName,
	maxTs *TS) (*mycmd.CmdBuilder, error) {
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
		dumpCmd.Append("-p", mycmd.Password(connInfo.Pass))
	}

	//	备份oplog时，不能使用archive模式.
	if archive {
		// do nothing. 备份oplog时，不能使用archive模式.
		// 生成未压缩的oplog.rs.bson文件. 再用zstd压缩.
	} else {
		// 非archive模式时，可以使用zip压缩. 这是为了兼容现有情况
		if zip {
			dumpCmd.Append("--gzip")
		}
	}

	dumpCmd.Append("-d", "local", "-c", "oplog.rs")

	// 如果maxTs为nil，则设置为当前时间. 如果不设置，在oplog比较大的时候，会一直持续备份，无法完成.
	if maxTs == nil {
		maxTs = &TS{Sec: uint32(time.Now().Unix()), I: 0}
	}

	if maxTs != nil {
		if strings.Contains(path.Base(mongoDumpBin), MongoVersionV100) {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s,"$lte":%s}}`, lastBackup.LastTs.JsonV2(), maxTs.JsonV2()))
		} else {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s,"$lte":%s}}`, lastBackup.LastTs.JsonV2(), maxTs.JsonV2()))
		}
	} else { // not reachable, will never happen, depcrecated
		if strings.Contains(path.Base(mongoDumpBin), MongoVersionV100) {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s}}`, lastBackup.LastTs.JsonV2()))
		} else {
			dumpCmd.Append("-q", fmt.Sprintf(`{"ts":{"$gte":%s}}`, lastBackup.LastTs.JsonV1()))
		}
	}

	return dumpCmd, nil
}

func buildDumpFullCmd(connInfo *mymongo.MongoHost, zip bool, archive bool, archiveFile string,
	lastBackup *BackupFileName, numParallelCollections int) (*mycmd.CmdBuilder, error) {
	// ./mongotools/mongodump.2.4  mongodump.3.0  mongodump.3.2  mongodump.3.4
	// mongodump.3.6  mongodump.4.0  mongodump.4.2

	// unused lastBackup
	_ = lastBackup
	_ = numParallelCollections
	_ = archiveFile

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
		dumpCmd.Append("-p", mycmd.Password(connInfo.Pass))
	}

	dumpCmd.Append("--oplog")

	// archive时，不使用zip, 而是使用zstd
	if archive {
		dumpCmd.Append("--archive=-")
	} else {
		// 非archive时, 可以使用zip
		if zip {
			dumpCmd.Append("--gzip")
		}
	}

	if numParallelCollections > 0 {
		dumpCmd.Append("-j", strconv.Itoa(numParallelCollections))
	}

	return dumpCmd, nil
}

func runCmdList(cmdList []*mycmd.MyExec) []error {
	var errorsList []error

	for _, e := range cmdList {
		if e == nil {
			continue
		}
		err := e.Start()
		if err != nil {
			errorsList = append(errorsList,
				errors.Errorf("Start failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err))
		}
	}

	for _, e := range cmdList {
		if e == nil {
			continue
		}
		err := e.Wait()
		if err != nil {
			errorsList = append(errorsList,
				errors.Errorf("Wait failed, cmd %s error: %v", e.CmdBuilder.GetCmdLine("", true), err))
		}
	}

	return errorsList
}
