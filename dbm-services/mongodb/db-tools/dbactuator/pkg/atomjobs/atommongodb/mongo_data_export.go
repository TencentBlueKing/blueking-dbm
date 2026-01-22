package atommongodb

import (
	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/logical"
	"encoding/json"
	"fmt"
	"net/url"
	"path"
	"reflect"
	"strings"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/mongo"
)

// MongoDB 数据导出
// 支持导出二进制数据或 json/csv
// 1. 分析参数，确定导出的库和表
// 2. 执行导出，并压缩成压缩包
// 3. 上传结果到制品库
// 4. 删除导出的压缩包

// MongoDataExportParams parameters for mongo dump data task
type MongoDataExportParams struct {
	BkDbmInstance  config.BkDbmLabel `json:"bk_dbm_instance"`
	IP             string            `json:"ip"`
	Port           int               `json:"port"`
	AdminUsername  string            `json:"adminUsername"`
	AdminPassword  string            `json:"adminPassword"`
	MaxConcurrency int               `json:"maxConcurrency"` // Maximum concurrency, default 4
	UploadDetail   UploadBkRepoParam `json:"upload_detail"`
	Args           struct {
		IsDumping bool        `json:"is_dumping"` // Whether using `mongodump` or `mongoexport`
		IsPartial bool        `json:"is_partial"` // If true, dump specified databases and collections
		NsFilter  NsFilterArg `json:"ns_filter"`  // Namespace filter for partial dumps
		Query     string      `json:"query"`      // Query filter for documents
		Fields    string      `json:"fields"`     // Specific fields to export
		Format    string      `json:"format"`     // Export format: json, csv (for mongoexport)
	} `json:"args"`
	FileName    string `json:"filename"`     // Local and remote filename
	PackagePath string `json:"package_path"` // Path of the mongodb-linux-xxx
}

// UploadBkRepoParam upload to bk repo param
type UploadBkRepoParam struct {
	BkCloudId    int        `json:"bk_cloud_id"`    // 所在的云区域
	DBCloudToken string     `json:"db_cloud_token"` // 云区域token
	FileServer   FileServer `json:"fileserver"`
}

// FileServer TODO
type FileServer struct {
	URL        string `json:"url"`         // 制品库地址
	Bucket     string `json:"bucket"`      // 目标bucket
	Password   string `json:"password"`    // 制品库 password
	Username   string `json:"username"`    // 制品库 username
	Project    string `json:"project"`     // 制品库 project
	UploadPath string `json:"upload_path"` // 上传路径
}

type mongoDataExport struct {
	BaseJob
	MongoDump   string
	MongoExport string
	ConfParams  *MongoDataExportParams
	MongoInst   *mymongo.MongoHost
	MongoClient *mongo.Client
	OutputPath  string // The tar file that was dumped or exported.
}

func (s *mongoDataExport) Param() string {
	o, _ := json.MarshalIndent(MongoDataExportParams{}, "", "\t")
	return string(o)
}

// NewMongoDataExportJob creates a new instance of mongoDumpDataJob
func NewMongoDataExportJob() jobruntime.JobRunner {
	return &mongoDataExport{}
}

// Name returns the name of the atomic task
func (s *mongoDataExport) Name() string {
	return "mongodb_data_export"
}

// Init initializes the job with runtime parameters
func (s *mongoDataExport) Init(runtime *jobruntime.JobGenericRuntime) error {
	// Initialize runtime and user
	s.runtime = runtime
	s.OsUser = ""

	if checkIsRootUser() {
		s.runtime.Logger.Error("This job cannot be executed as root user")
		return errors.New("This job cannot be executed as root user")
	}

	// Parse parameters from payload
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}

	// Parameter validation
	if err := s.validateParams(); err != nil {
		return errors.Wrap(err, "parameter validation failed")
	}

	// Set default values
	if s.ConfParams.MaxConcurrency <= 0 {
		s.ConfParams.MaxConcurrency = 4
	}

	// Set default format for mongoexport
	if !s.ConfParams.Args.IsDumping && s.ConfParams.Args.Format == "" {
		s.ConfParams.Args.Format = "json"
	}

	// Initialize MongoDB connection
	s.MongoInst = mymongo.NewMongoHost(
		s.ConfParams.IP, fmt.Sprintf("%d", s.ConfParams.Port),
		"admin", s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "", s.ConfParams.IP)

	// Prepare mongo client and mongodump path
	client, err := s.MongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, "Connect")
	}
	s.MongoClient = client

	// Extract and setup MongoDB tools
	if err := s.setupMongoTools(); err != nil {
		return errors.Wrap(err, "setupMongoTools")
	}

	return nil

}

// setupMongoTools extracts MongoDB package and sets up tool paths
func (s *mongoDataExport) setupMongoTools() error {
	if !util.FileExists(s.ConfParams.PackagePath) {
		return errors.Errorf("package path %s not found", s.ConfParams.PackagePath)
	}

	// Extract package base name (e.g., mongodb-linux-x86_64-3.4.20.tar.gz -> mongodb-linux-x86_64-3.4.20)
	pkgBaseName := strings.TrimSuffix(path.Base(s.ConfParams.PackagePath), ".tar.gz")

	// Use /data/dbbak/mongodb-tools as extraction directory (where mysql user has permissions)
	binDir := path.Join(consts.GetMongoBackupDir(), "dbbak", "mongodb-tools")
	unTarPath := path.Join(binDir, pkgBaseName)

	// Create binDir with mysql ownership if it doesn't exist
	if !util.FileExists(binDir) {
		if err := util.MkDirsIfNotExists([]string{binDir}); err != nil {
			return errors.Wrap(err, "failed to create mongodb-tools directory")
		}
		if err := util.LocalDirChownMysql(binDir); err != nil {
			return errors.Wrap(err, "failed to chown mongodb-tools directory")
		}
	}

	// Untar the package to binDir if not already extracted
	if !util.FileExists(unTarPath) {
		s.runtime.Logger.Info("Extracting MongoDB package to %s", binDir)
		tarCmd := fmt.Sprintf("tar -zxf %s -C %s", s.ConfParams.PackagePath, binDir)
		if _, err := util.RunBashCmd(tarCmd, "", nil, 2*time.Minute); err != nil {
			s.runtime.Logger.Error("Failed to extract package: %s", err)
			return errors.Wrap(err, "untar MongoDB package")
		}
		s.runtime.Logger.Info("Successfully extracted MongoDB package to %s", unTarPath)
	} else {
		s.runtime.Logger.Info("MongoDB package already extracted at %s", unTarPath)
	}

	s.MongoDump = path.Join(unTarPath, "bin", "mongodump")
	s.MongoExport = path.Join(unTarPath, "bin", "mongoexport")

	// Verify the binaries exist
	if !util.FileExists(s.MongoDump) {
		return errors.Errorf("mongodump binary not found at %s", s.MongoDump)
	}
	if !util.FileExists(s.MongoExport) {
		return errors.Errorf("mongoexport binary not found at %s", s.MongoExport)
	}

	s.runtime.Logger.Info("MongoDB tools configured: mongodump=%s, mongoexport=%s", s.MongoDump, s.MongoExport)

	return nil
}

// Run executes the atomic task
func (s *mongoDataExport) Run() error {

	// Fetch concurrency lock
	lock, err := s.GetConcurrentLock(s.ConfParams.MaxConcurrency)
	if err != nil {
		s.runtime.Logger.Error("GetConcurrentLock failed, err:%s", err)
		return errors.Wrap(err, "GetConcurrentLock")
	}
	defer lock.Unlock()

	outputPath, err := s.prepareOutputPath()
	if err != nil {
		return errors.Wrap(err, "prepareOutputPath")
	}

	if s.ConfParams.Args.IsDumping {
		err = s.doDumpData(outputPath)
	} else {
		err = s.doExportData(outputPath)
	}
	if err != nil {
		return err
	}

	// Upload tar file to bkrepo.
	if err := s.ConfParams.UploadDetail.Upload(s.OutputPath); err != nil {
		s.runtime.Logger.Error("Failed to upload result tar file: %v", err)
		return errors.Wrap(err, "uploadTarFile")
	}
	s.runtime.Logger.Info("Upload to to %s successfully", s.ConfParams.UploadDetail.FileServer.URL)

	return errors.Wrap(s.removeDir(s.OutputPath), "deleteTarFile")
}

// doDumpData performs the actual data dump operation
// outputPath e.g. "/data/dbbak/mongodb-data-export/<domain>_<time>_<set_name>" as dir
func (s *mongoDataExport) doDumpData(outputPath string) error {
	helper := logical.NewMongoDumpHelper(s.MongoInst, s.MongoDump,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "admin", s.OsUser)

	var err error
	if s.ConfParams.Args.IsPartial {
		err = s.dumpPartialData(helper, outputPath)
	} else {
		err = s.dumpAllData(helper, outputPath)
	}

	if err != nil {
		return err
	}

	if err := s.compressOutput(outputPath); err != nil {
		return errors.Wrap(err, "Failed to compress output")
	}

	return err
}

// Upload uploads "<filename>.tar" to bkrepo
func (c UploadBkRepoParam) Upload(filePath string) (err error) {
	if reflect.DeepEqual(c.FileServer, FileServer{}) {
		return fmt.Errorf("file server is empty")
	}

	if filePath == "" {
		return fmt.Errorf("file path is empty")
	}

	if !util.FileExists(filePath) {
		return fmt.Errorf("file does not exist: %s", filePath)
	}

	// Use the actual file name from the path
	fileName := path.Base(filePath)
	r := path.Join("generic", c.FileServer.Project, c.FileServer.Bucket, c.FileServer.UploadPath)
	uploadUrl, err := url.JoinPath(c.FileServer.URL, r, "/")
	if err != nil {
		return fmt.Errorf("call url joinPath failed %s", err.Error())
	}
	if c.BkCloudId == 0 {
		uploadUrl, err = url.JoinPath(
			c.FileServer.URL, path.Join(
				"/generic", c.FileServer.Project,
				c.FileServer.Bucket, c.FileServer.UploadPath, fileName,
			),
		)
		if err != nil {
			return fmt.Errorf("call url joinPath failed %s", err.Error())
		}
	}

	resp, err := bkrepo.UploadFile(
		filePath, uploadUrl, c.FileServer.Username, c.FileServer.Password,
		c.BkCloudId, c.DBCloudToken,
	)
	if err != nil {
		return fmt.Errorf("upload file error %s", err.Error())
	}
	if resp.Code != 0 {
		errMsg := fmt.Sprintf(
			"upload response code is %d,response msg:%s,traceId:%s",
			resp.Code,
			resp.Message,
			resp.RequestId,
		)
		return fmt.Errorf("%s", errMsg)
	}

	var uploadRespdata bkrepo.UploadRespData
	if err := json.Unmarshal(resp.Data, &uploadRespdata); err != nil {
		return fmt.Errorf("unmarshal upload response data failed %s", err.Error())
	}

	return nil
}

// prepareOutputPath prepares the output directory for dump files
func (s *mongoDataExport) prepareOutputPath() (string, error) {
	// Use default backup path structure
	outputPath := path.Join(consts.GetMongoBackupDir(), "dbbak", "mongodb-data-export", s.ConfParams.FileName)

	err := util.MkDirsIfNotExists([]string{outputPath})
	if err != nil {
		return "", errors.Wrap(err, "MkDirsIfNotExists")
	}

	err = util.LocalDirChownMysql(outputPath)
	if err != nil {
		return "", errors.Wrap(err, "LocalDirChownMysql")
	}

	return outputPath, nil
}

// dumpPartialData performs partial data dump with namespace filtering
func (s *mongoDataExport) dumpPartialData(helper *logical.MongoDumpHelper, outputPath string) error {
	partialArgs := s.ConfParams.Args.NsFilter
	filter := logical.NewNsFilter(
		partialArgs.DbList, partialArgs.IgnoreDbList,
		partialArgs.ColList, partialArgs.IgnoreColList)

	var cmdLineList []string
	var cmdLine string
	var err error

	// Use query-enabled dump if query is provided
	if s.ConfParams.Args.Query != "" {
		s.runtime.Logger.Info("Using query filter: %s", s.ConfParams.Args.Query)
		cmdLineList, cmdLine, _, _, err = helper.DumpPartial(outputPath, "dump.log", filter, &s.ConfParams.Args.Query)
	} else {
		cmdLineList, cmdLine, _, _, err = helper.DumpPartial(outputPath, "dump.log", filter, nil)
	}

	if err != nil {
		if errors.Is(err, logical.ErrorNoMatchDb) {
			s.runtime.Logger.Warn("NoMatchDb - no databases matched the filter criteria")
			return nil
		} else {
			s.runtime.Logger.Error("exec cmd fail, cmd: %s, error:%s", cmdLine, err)
			return errors.Wrap(err, "DumpPartial")
		}
	}

	s.runtime.Logger.Info("exec cmd success, cmd: %+v", cmdLineList)
	return nil
}

// dumpAllData performs full data dump
func (s *mongoDataExport) dumpAllData(helper *logical.MongoDumpHelper, outputPath string) error {
	var cmdLine string
	var err error

	// Use query-enabled dump if query is provided
	cmdLine, err = helper.LogicalDumpAll(outputPath, "dump.log")

	if err != nil {
		s.runtime.Logger.Error("exec cmd fail, cmd: %s, error:%s", cmdLine, err)
		return errors.Wrap(err, "LogicalDumpAll")
	}

	s.runtime.Logger.Info("exec cmd success, cmd: %s", cmdLine)
	return nil
}

// Retry returns the number of retry attempts
func (s *mongoDataExport) Retry() uint {
	return 2
}

// Rollback performs rollback operations
func (s *mongoDataExport) Rollback() error {
	return nil
}

// validateParams validates the input parameters
func (s *mongoDataExport) validateParams() error {
	if s.ConfParams == nil {
		return errors.New("ConfParams is nil")
	}

	// Required parameters
	if s.ConfParams.IP == "" {
		return errors.New("IP is required")
	}
	if s.ConfParams.Port <= 0 {
		return errors.New("Port must be positive")
	}
	if s.ConfParams.AdminUsername == "" {
		return errors.New("AdminUsername is required")
	}
	if s.ConfParams.AdminPassword == "" {
		return errors.New("AdminPassword is required")
	}

	// Validate export format for mongoexport
	if !s.ConfParams.Args.IsDumping {
		if s.ConfParams.Args.Format != "" && s.ConfParams.Args.Format != "json" && s.ConfParams.Args.Format != "csv" {
			return errors.New("format must be 'json' or 'csv' for mongoexport")
		}
		// For mongoexport, we need specific collections
		if !s.ConfParams.Args.IsPartial {
			return errors.New("mongoexport requires partial mode with specific collections")
		}
		// csv has to be used with fields
		if s.ConfParams.Args.Format == "csv" && s.ConfParams.Args.Fields == "" {
			return errors.New("csv format requires fields parameter")
		}
	}

	// Validate namespace filter for partial exports
	if s.ConfParams.Args.IsPartial {
		nsFilter := s.ConfParams.Args.NsFilter
		if len(nsFilter.DbList) == 0 && len(nsFilter.IgnoreDbList) == 0 &&
			len(nsFilter.ColList) == 0 && len(nsFilter.IgnoreColList) == 0 {
			return errors.New("partial mode requires at least one namespace filter")
		}
	}

	return nil
}

// compressOutput compresses the outputPath and then remove it
func (s *mongoDataExport) compressOutput(outputPath string) error {
	// Create tar file
	targetFolder := path.Base(outputPath)
	tarFile := fmt.Sprintf("%s.tar", targetFolder)
	tarPath := path.Join(path.Dir(outputPath), tarFile)

	tarCmd := mycmd.New("tar", "cvf", tarPath, "-C", path.Dir(outputPath), targetFolder)
	execResult, err := tarCmd.Run(time.Hour * 2)
	s.runtime.Logger.Info("exec cmd: %q, exitCode:%d, err:%v", tarCmd.GetCmdLine2(true), execResult.ExitCode, err)

	if execResult.ExitCode != 0 {
		return errors.Wrap(err, "tar compression failed")
	}

	// Remove original directory after successful compression
	if err = s.removeDir(outputPath); err != nil {
		s.runtime.Logger.Warn("Failed to remove original directory after compression: %v", err)
	}

	// Update output path to compressed file
	s.OutputPath = tarPath
	s.runtime.Logger.Info("Output compressed to: %s", tarPath)

	return nil
}

// doExportData performs mongoexport operation
func (s *mongoDataExport) doExportData(outputPath string) error {
	// mongoexport requires specific database and collection
	if !s.ConfParams.Args.IsPartial {
		return errors.New("mongoexport requires partial mode with specific collections")
	}
	partialArgs := s.ConfParams.Args.NsFilter
	filter := logical.NewNsFilter(
		partialArgs.DbList, partialArgs.IgnoreDbList,
		partialArgs.ColList, partialArgs.IgnoreColList)

	helper := logical.NewMongoExportHelper(s.MongoInst, s.MongoExport,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "admin", s.OsUser)

	args := &logical.ExportArgs{
		Query:  s.ConfParams.Args.Query,
		Fields: s.ConfParams.Args.Fields,
		Format: s.ConfParams.Args.Format,
	}

	_, cmdLine, err := helper.ExportWithFilter(outputPath, filter, args)
	if err != nil {
		s.runtime.Logger.Error("exec cmd failed, cmd: %s, err: %s", cmdLine, err)
		return errors.Wrap(err, "doExportData")
	}

	if err = s.compressOutput(outputPath); err != nil {
		return errors.Wrap(err, "compressOutput")
	}

	return err
}
