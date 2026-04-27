package atommongodb

import (
	"bytes"
	"encoding/json"
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// AddUserConfParams 参数
type AddUserConfParams struct {
	IP            string              `json:"ip" validate:"required"`
	Port          int                 `json:"port" validate:"required"`
	InstanceType  string              `json:"instanceType" validate:"required"`
	Username      string              `json:"username" validate:"required"`
	Password      string              `json:"password" validate:"required"`
	AdminUsername string              `json:"adminUsername"`
	AdminPassword string              `json:"adminPassword"`
	AuthDb        string              `json:"authDb"`        // 为方便管理用户，验证库默认为admin库
	DbsPrivileges []common.Privileges `json:"dbsPrivileges"` // 业务库 以及权限 [{"db":xxx,"privileges":[xxx,xxx]}]
}

// AddUser 添加用户
// 1. 添加bootstrap阶段的用户
// 2. 添加正常阶段的用户
type AddUser struct {
	BaseJob
	runtime       *jobruntime.JobGenericRuntime
	BinDir        string
	Mongo         string
	PrimaryIP     string
	PrimaryPort   int
	OsUser        string
	ScriptContent string
	ConfParams    *AddUserConfParams
	isBootstrap   bool // 是否是bootstrap阶段
}

func sanitizeSensitiveText(input string, secrets ...string) string {
	out := input
	for _, secret := range secrets {
		if strings.TrimSpace(secret) == "" {
			continue
		}
		out = strings.ReplaceAll(out, secret, "***")
	}
	return out
}

func (u *AddUser) userWithAuthDB() string {
	authDB := u.ConfParams.AuthDb
	if strings.TrimSpace(authDB) == "" {
		authDB = "admin"
	}
	return fmt.Sprintf("%s@%s", u.ConfParams.Username, authDB)
}

// NewAddUser 实例化结构体
func NewAddUser() jobruntime.JobRunner {
	return &AddUser{}
}

// Name 获取原子任务的名字
func (u *AddUser) Name() string {
	return "add_user"
}

// Run 运行原子任务
func (u *AddUser) Run() error {
	u.runtime.Logger.Info("start to run addUser")
	// 生成脚本内容
	if err := u.makeScriptContent(); err != nil {
		u.runtime.Logger.Error("make script content of addUser fail, error:%s", err)
		return err
	}

	if u.isBootstrap {
		u.runtime.Logger.Info("start to add first admin user %s", u.userWithAuthDB())
		return u.addFirstAdminUser()
	}
	u.runtime.Logger.Info("start to add normal user %s", u.userWithAuthDB())
	return u.addNormalUser()
}

// Retry 重试
func (u *AddUser) Retry() uint {
	return 2
}

// Rollback 回滚
func (u *AddUser) Rollback() error {
	return nil
}

// Init 初始化
func (u *AddUser) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	u.runtime = runtime
	u.runtime.Logger.Info("start to init")
	u.BinDir = consts.GetMongoBinDir()
	u.Mongo = filepath.Join(u.BinDir, "mongodb", "bin", "mongo")
	u.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(u.runtime.PayloadDecoded), &u.ConfParams); err != nil {
		u.runtime.Logger.Error("get parameters of addUser fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of addUser fail by json.Unmarshal, error:%s", err)
	}

	u.isBootstrap = u.ConfParams.AdminUsername == "" && u.ConfParams.AdminPassword == ""

	// 获取primary信息
	if u.ConfParams.InstanceType == "mongos" {
		u.PrimaryIP = u.ConfParams.IP
		u.PrimaryPort = u.ConfParams.Port
		u.runtime.Logger.Info("init resolved mongos=%s:%d", u.PrimaryIP, u.PrimaryPort)
	} else {
		primaryAddr, err := common.NoAuthGetPrimaryInfo(u.Mongo, u.ConfParams.IP, u.ConfParams.Port)

		if err != nil {
			u.runtime.Logger.Error("resolve primary db info of addUser fail, error:%s", err)
			return fmt.Errorf("resolve primary db info of addUser fail, error:%s", err)
		}
		if primaryAddr == "" {
			u.runtime.Logger.Error("resolve primary db info of addUser fail, error:%s", err)
			return fmt.Errorf("resolve primary db info of addUser fail, error:%s", err)
		}
		primaryAddrSlice := strings.Split(primaryAddr, ":")
		if len(primaryAddrSlice) != 2 {
			u.runtime.Logger.Error("resolve primary db info of addUser fail, error:%s", err)
			return fmt.Errorf("resolve primary db info of addUser fail, error:%s", err)
		}
		u.PrimaryIP = primaryAddrSlice[0]
		u.PrimaryPort, err = strconv.Atoi(primaryAddrSlice[1])
		if err != nil {
			u.runtime.Logger.Error("resolve primary db info port parse fail, addr:%s, error:%s", primaryAddr, err)
			return fmt.Errorf("resolve primary db info port parse fail, addr:%s, error:%s", primaryAddr, err)
		}
		u.runtime.Logger.Info("init resolved primary=%s:%d", u.PrimaryIP, u.PrimaryPort)
	}
	u.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := u.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (u *AddUser) checkParams() error {
	validate := validator.New()
	u.runtime.Logger.Info("start to validate parameters of addUser")
	if err := validate.Struct(u.ConfParams); err != nil {
		return fmt.Errorf("validate parameters of addUser fail, error:%s", err)
	}
	u.runtime.Logger.Info("validate parameters of addUser successfully")
	return nil
}

// makeScriptContent 生成user配置内容
func (u *AddUser) makeScriptContent() error {
	u.runtime.Logger.Info("start to make script content")
	// 获取mongo版本
	mongoName := "mongod"
	if u.ConfParams.InstanceType == "mongos" {
		mongoName = "mongos"
	}
	version, err := common.CheckMongoVersion(u.BinDir, mongoName)
	if err != nil {
		u.runtime.Logger.Error("check mongo version fail, error:%s", err)
		return fmt.Errorf("check mongo version fail, error:%s", err)
	}
	mainVersion, _ := strconv.ParseFloat(strings.Join(strings.Split(version, ".")[0:2], "."), 64)
	user := common.NewMongoUser(mainVersion)
	// 判断验证db
	if u.ConfParams.AuthDb == "" {
		u.ConfParams.AuthDb = "admin"
	}
	// 进行初始化
	user.Init(u.ConfParams.Username, u.ConfParams.Password, u.ConfParams.DbsPrivileges)
	// 获取创建用户内容
	content, err := user.GetContent()
	if err != nil {
		u.runtime.Logger.Error("make config content of addUser fail, error:%s", err)
		return fmt.Errorf("make config content of addUser fail, error:%s", err)
	}
	if mainVersion >= 2.6 {
		u.ScriptContent = strings.Join([]string{"db",
			fmt.Sprintf("createUser(%s)", content)}, ".")
		u.runtime.Logger.Info("make script content successfully")
		return nil
	}
	u.ScriptContent = strings.Join([]string{"db",
		fmt.Sprintf("addUser(%s)", content)}, ".")
	u.runtime.Logger.Info("make script content successfully")

	return nil
}

func (u *AddUser) getAuthDB() string {
	authDB := u.ConfParams.AuthDb
	if strings.TrimSpace(authDB) == "" {
		authDB = "admin"
	}
	return authDB
}

// checkUser 检查用户是否存在
func (u *AddUser) checkUser() (bool, error) {
	time.Sleep(time.Second * 3)
	authDB := u.getAuthDB()
	script := fmt.Sprintf(`u=db.getSiblingDB("%s").getUser("%s"); if(!u){print("MISSING");}else{print("EXISTS");}`, authDB, u.ConfParams.Username)
	var opts []interface{}
	if u.isBootstrap {
		// Use 127.0.0.1 so MongoDB's localhost exception applies (no users exist yet).
		opts = []interface{}{
			"--host", "127.0.0.1",
			"--port", strconv.Itoa(u.PrimaryPort),
			"--quiet",
			"--eval", script,
			authDB,
		}
	} else {
		opts = []interface{}{
			"-u", u.ConfParams.AdminUsername,
			"-p", mycmd.Password(u.ConfParams.AdminPassword),
			"--host", u.PrimaryIP,
			"--port", strconv.Itoa(u.PrimaryPort),
			"--authenticationDatabase=admin",
			"--quiet",
			"--eval", script,
			authDB,
		}
	}
	result, err := u.runMongoCmd(opts...)
	if err != nil {
		if u.isBootstrap {
			// Rerun-compatible fallback: once auth is enabled, no-auth usersInfo fails.
			// Try the same check with target user credential regardless of no-auth failure reason.
			authOpts := []interface{}{
				"-u", u.ConfParams.Username,
				"-p", mycmd.Password(u.ConfParams.Password),
				"--host", u.PrimaryIP,
				"--port", strconv.Itoa(u.PrimaryPort),
				"--authenticationDatabase=" + authDB,
				"--quiet",
				"--eval", script,
				authDB,
			}
			result, err = u.runMongoCmd(authOpts...)
			if err != nil {
				return false, err
			}
			resultUpper := strings.ToUpper(result)
			return strings.Contains(resultUpper, "EXISTS"), nil
		}
		return false, err
	}
	resultUpper := strings.ToUpper(result)
	return strings.Contains(resultUpper, "EXISTS"), nil
}

func (u *AddUser) runMongoCmd(opts ...interface{}) (string, error) {
	var stdoutBuf bytes.Buffer
	var stderrBuf bytes.Buffer
	args := append([]any{u.Mongo}, opts...)
	cmdBuilder := mycmd.New(args...)
	maskedCmdline := sanitizeSensitiveText(
		cmdBuilder.GetCmdLine("", true),
		u.ConfParams.Password,
		u.ConfParams.AdminPassword,
	)
	ret, err := cmdBuilder.Run3(60*time.Second, &stdoutBuf, &stderrBuf)
	stdout := strings.TrimSpace(stdoutBuf.String())
	stderr := strings.TrimSpace(stderrBuf.String())
	if err != nil || ret.ExitCode != 0 {
		return "", fmt.Errorf("run mongo cmd fail: %w (cmd=%q, exitCode=%d, stdout=%q, stderr=%q)", err,
			maskedCmdline, ret.ExitCode, stdout, stderr)
	}
	return stdout, nil
}

// changePrimaryPriority 修改复制集主节点优先级
func (u *AddUser) changePrimaryPriority() error {
	u.runtime.Logger.Info("start to execute changePrimaryPriority script")
	// 修改优先级
	script := fmt.Sprintf("cfg = rs.conf();\ncfg.members[0].priority=%d;\nrs.reconfig(cfg);", 1)
	u.runtime.Logger.Info("execute changePrimaryPriority script:\n%s", script)
	opts := []interface{}{
		"--host", u.PrimaryIP,
		"--port", strconv.Itoa(u.PrimaryPort),
		"-u", u.ConfParams.Username,
		"-p", mycmd.Password(u.ConfParams.Password),
		"--quiet",
		"--eval", script,
		"admin",
	}
	if _, err := u.runMongoCmd(opts...); err != nil {
		u.runtime.Logger.Error("execute changePrimaryPriority script fail, error:%s", err)
		return fmt.Errorf("execute changePrimaryPriority script fail, error:%s", err)
	}
	u.runtime.Logger.Info("execute changePrimaryPriority script successfully")

	return nil
}

func isUserAlreadyExistsErr(err error) bool {
	if err == nil {
		return false
	}
	errStr := strings.ToLower(err.Error())
	return strings.Contains(errStr, "already exists") ||
		strings.Contains(errStr, "duplicatekey") ||
		strings.Contains(errStr, "duplicate key")
}

func (u *AddUser) handleExistingNormalUser() error {
	compatible, verifyErr := u.verifyExistingUserCompatible()
	if verifyErr != nil {
		u.runtime.Logger.Error("verify existing user compatibility fail, error:%s", verifyErr)
		return fmt.Errorf("verify existing user compatibility fail, error:%s", verifyErr)
	}
	if compatible {
		u.runtime.Logger.Warn("user:%s already exists and definition matches exactly, skip add_user", u.userWithAuthDB())
		return nil
	}
	u.runtime.Logger.Error("user:%s already exists but definition does not match exactly", u.userWithAuthDB())
	return fmt.Errorf("user:%s already exists but definition does not match exactly", u.userWithAuthDB())
}

func (u *AddUser) verifyExistingUserCompatible() (bool, error) {
	exists, err := u.checkUser()
	if err != nil {
		return false, err
	}
	if !exists {
		return false, nil
	}
	credentialOK, err := u.verifyUserCredential()
	if err != nil {
		return false, err
	}
	if !credentialOK {
		return false, nil
	}
	rolesOK, err := u.verifyUserRoles()
	if err != nil {
		return false, err
	}
	return rolesOK, nil
}

func (u *AddUser) verifyExistingUserCompatibleWithPrimaryFallback() (bool, error) {
	compatible, err := u.verifyExistingUserCompatible()
	if err == nil {
		return compatible, nil
	}
	// Retry path for idempotent reruns: if local endpoint is no longer primary,
	// or the local endpoint now requires authentication, discover current primary
	// with the target user's credential and verify again.
	errStr := strings.ToLower(err.Error())
	if !strings.Contains(errStr, "not master") &&
		!strings.Contains(errStr, "not primary") &&
		!strings.Contains(errStr, "requires authentication") &&
		!strings.Contains(errStr, "unauthorized") {
		return false, err
	}
	primaryInfo, pErr := common.AuthGetPrimaryInfo(
		u.Mongo, u.ConfParams.Username, u.ConfParams.Password, u.ConfParams.IP, u.ConfParams.Port,
	)
	if pErr != nil || primaryInfo == "" {
		return false, err
	}
	infoParts := strings.Split(primaryInfo, ":")
	if len(infoParts) != 2 {
		return false, err
	}
	primaryPort, convErr := strconv.Atoi(infoParts[1])
	if convErr != nil {
		return false, err
	}
	u.runtime.Logger.Warn(
		"retry user compatibility check on discovered primary=%s after non-primary error",
		primaryInfo,
	)
	u.PrimaryIP = infoParts[0]
	u.PrimaryPort = primaryPort
	return u.verifyExistingUserCompatible()
}

func (u *AddUser) verifyUserCredential() (bool, error) {
	authDB := u.getAuthDB()
	opts := []interface{}{
		"-u", u.ConfParams.Username,
		"-p", mycmd.Password(u.ConfParams.Password),
		"--host", u.PrimaryIP,
		"--port", strconv.Itoa(u.PrimaryPort),
		"--authenticationDatabase=" + authDB,
		"--quiet",
		"--eval", "print(1)",
	}
	result, err := u.runMongoCmd(opts...)
	if err != nil {
		return false, nil
	}
	return strings.TrimSpace(result) == "1", nil
}

func (u *AddUser) verifyUserRoles() (bool, error) {
	authDB := u.getAuthDB()
	// No admin credential: skip role-detail check and rely on credential check only.
	// This avoids false-negative MISSING when target user lacks listUsers/userAdmin privilege.
	if u.ConfParams.AdminUsername == "" && u.ConfParams.AdminPassword == "" {
		u.runtime.Logger.Warn("verifyUserRoles skipped: admin credential is empty, fallback to credential-only check")
		return true, nil
	}

	expectedPairs := make([]string, 0)
	for _, dbPrivileges := range u.ConfParams.DbsPrivileges {
		for _, privilege := range dbPrivileges.Privileges {
			expectedPairs = append(expectedPairs, fmt.Sprintf("%s@%s", privilege, dbPrivileges.Db))
		}
	}
	sort.Strings(expectedPairs)
	expected := strings.Join(expectedPairs, ",")
	script := fmt.Sprintf(
		`u=db.getSiblingDB("%s").getUser("%s"); if(!u){print("MISSING");}else{print(u.roles.map(function(r){return r.role+"@"+r.db;}).sort().join(","));}`,
		authDB, u.ConfParams.Username,
	)
	opts := []interface{}{
		"-u", u.ConfParams.AdminUsername,
		"-p", mycmd.Password(u.ConfParams.AdminPassword),
		"--host", u.PrimaryIP,
		"--port", strconv.Itoa(u.PrimaryPort),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", script,
		authDB,
	}
	result, err := u.runMongoCmd(opts...)
	if err != nil {
		return false, nil
	}
	actual := strings.TrimSpace(result)
	if actual == "MISSING" {
		return false, nil
	}
	return actual == expected, nil
}

func (u *AddUser) buildNormalUserAddOpts() []interface{} {
	return []interface{}{
		"-u", u.ConfParams.AdminUsername,
		"-p", mycmd.Password(u.ConfParams.AdminPassword),
		"--host", u.PrimaryIP,
		"--port", strconv.Itoa(u.PrimaryPort),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", u.ScriptContent,
		u.ConfParams.AuthDb,
	}
}

func (u *AddUser) buildBootstrapDbaAddOpts() []interface{} {
	// Bootstrap (first admin user) relies on MongoDB's localhost exception, which only applies to
	// connections from 127.0.0.1. The external IP returned by rs.isMaster().primary does NOT
	// trigger the exception even when dbactuator runs on the same host.
	return []interface{}{
		"--host", "127.0.0.1",
		"--port", strconv.Itoa(u.PrimaryPort),
		"--quiet",
		"--eval", u.ScriptContent,
		u.ConfParams.AuthDb,
	}
}

func (u *AddUser) addNormalUser() error {
	// 检查用户是否存在
	flag, err := u.checkUser()
	if err != nil {
		return err
	}
	if flag {
		return u.handleExistingNormalUser()
	}
	return u.runAddNormalUserScript()
}

func (u *AddUser) addFirstAdminUser() error {
	// Idempotency optimization for bootstrap path:
	// if the target user can already authenticate, treat as success and skip addUser.
	credentialOK, err := u.verifyUserCredential()
	if err != nil {
		u.runtime.Logger.Warn("bootstrap pre-check verify credential fail, continue add user: %v", err)
	}

	if credentialOK {
		u.runtime.Logger.Warn("bootstrap addUser skipped: user %s can already authenticate", u.userWithAuthDB())
		return nil
	}

	// 要求PrimaryIp == IP 否则报错. 除非ConfParams.IP是127.0.x.x (测试环境)
	if u.PrimaryIP != u.ConfParams.IP {
		if !strings.HasPrefix(u.ConfParams.IP, "127.0.0.") {
			u.runtime.Logger.Error("bootstrap addUser must run on the same host as the primary: %s", u.PrimaryIP)
			return fmt.Errorf("add user:%s fail, primary ip is not local ip: %s", u.userWithAuthDB(), u.PrimaryIP)
		}
	}

	// 复制集初始化后，马上创建db管理员用户，需要等3秒
	time.Sleep(time.Second * 3)
	if err := u.runAddFirstAdminUserScript(); err != nil {
		return err
	}
	// Simplified success criteria for bootstrap flow:
	// after addUser, authentication success is enough.
	credentialOK, err = u.verifyUserCredential()
	if err != nil {
		return err
	}
	if !credentialOK {
		return fmt.Errorf("add user:%s fail, authentication verify failed", u.userWithAuthDB())
	}
	// 创建dba用户后，修改primary优先级
	if err := u.changePrimaryPriority(); err != nil {
		return err
	}
	return nil
}

func (u *AddUser) runAddNormalUserScript() error {
	// 执行脚本
	u.runtime.Logger.Info("start to execute addUser script")
	if _, err := u.runMongoCmd(u.buildNormalUserAddOpts()...); err != nil {
		if !isUserAlreadyExistsErr(err) {
			u.runtime.Logger.Error("execute addUser script fail, error:%s", err)
			return fmt.Errorf("execute addUser script fail, error:%s", err)
		}
		if handleErr := u.handleExistingNormalUser(); handleErr != nil {
			return handleErr
		}
		u.runtime.Logger.Warn("addUser script failed but existing user definition matches exactly, continue: %v", err)
	}
	u.runtime.Logger.Info("execute addUser script successfully")
	return u.checkAddUserSuccess()
}

func (u *AddUser) runAddFirstAdminUserScript() error {
	// 执行脚本
	u.runtime.Logger.Info("start to execute addUser script for %s", u.userWithAuthDB())
	if _, err := u.runMongoCmd(u.buildBootstrapDbaAddOpts()...); err != nil {
		compatible, verifyErr := u.verifyExistingUserCompatibleWithPrimaryFallback()
		if verifyErr != nil {
			u.runtime.Logger.Error("verify existing user compatibility fail, error:%s", verifyErr)
			return fmt.Errorf("verify existing user compatibility fail, error:%s", verifyErr)
		}
		if compatible {
			u.runtime.Logger.Warn("addUser script failed but existing user definition matches exactly, continue: %v", err)
		} else if isUserAlreadyExistsErr(err) {
			u.runtime.Logger.Error("user:%s already exists but definition does not match exactly",
				u.userWithAuthDB())
			return fmt.Errorf("user:%s already exists but definition does not match exactly",
				u.userWithAuthDB())
		} else {
			u.runtime.Logger.Error("execute addUser script fail, error:%s", err)
			return fmt.Errorf("execute addUser script fail, error:%s", err)
		}
	}
	u.runtime.Logger.Info("execute addUser script successfully")
	return nil
}

func (u *AddUser) checkAddUserSuccess() error {
	// 检查用户是否存在
	flag, err := u.checkUser()
	if err != nil {
		u.runtime.Logger.Error("check add user:%s fail, error:%s", u.userWithAuthDB(), err)
		return fmt.Errorf("check add user:%s fail, error:%s", u.userWithAuthDB(), err)
	}
	if !flag {
		u.runtime.Logger.Error("add user:%s fail, user not found", u.userWithAuthDB())
		return fmt.Errorf("add user:%s fail, user not found", u.userWithAuthDB())
	}
	return nil
}
