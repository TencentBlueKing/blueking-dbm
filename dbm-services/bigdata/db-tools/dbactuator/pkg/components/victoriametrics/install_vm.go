// Package victoriametrics TODO
package victoriametrics

import (
	"encoding/json"
	"fmt"
	"os"
	"os/user"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/vmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InstallVMComp TODO
type InstallVMComp struct {
	GeneralParam    *components.GeneralParam
	Params          *InstallVMParams
	RollBackContext rollback.RollBackObjects
}

// InstallVMParams TODO
type InstallVMParams struct {
	InsertConfig      json.RawMessage `json:"insert_config"`                   // vminsert配置
	SelectConfig      json.RawMessage `json:"select_config"`                   // vmselect配置
	StorageConfig     json.RawMessage `json:"storage_config"`                  // vmstorage配置
	AuthConfig        json.RawMessage `json:"auth_config"`                     // vmauth配置
	VMVersion         string          `json:"vm_version"  validate:"required"` // vm的版本
	DataPath          string          `json:"data_path" `                      // vmstorage的路径
	InsertPort        int             `json:"insert_port"`                     // vminsert监听端口
	SelectPort        int             `json:"select_port"`                     // vmselect监听端口
	RetentionPeriod   string          `json:"retention_period"`                // 数据保留时间，单位月
	ReplicationFactor int             `json:"replication_factor"`              // 数据存几份
	StorageNode       string          `json:"storage_node"`                    // vmstorage地址,eg. ip1:8401,ip2,8401
	Host              string          `json:"host"`                            // 本机ip
	InsertNodes       string          `json:"insert_nodes"`                    // vminsert列表, eg. ip1:8480,ip2:8480
	SelectNodes       string          `json:"select_nodes"`                    // vmselect列表, eg. ip1:8481,ip2:8481
}

// InitDefaultParam TODO
func (i *InstallVMComp) InitDefaultParam() (err error) {
	logger.Info("start InitDefaultParam")
	if i.Params.DataPath == "" {
		i.Params.DataPath = cst.DefaultVMDataDir
	}

	return nil
}

// InitVM TODO
/*
创建实例相关的数据，日志目录以及修改权限
*/
func (i *InstallVMComp) InitVM() error {

	dataDir := i.Params.DataPath
	if dataDir == "" {
		dataDir = cst.DefaultVMDataDir
	}
	host := i.Params.Host
	envDir := cst.DefaultVMEnv
	logDir := cst.DefaultVMLogDir
	execUser := cst.DefaultExecUser
	logger.Info("检查用户[%s]是否存在", execUser)
	if _, err := user.Lookup(execUser); err != nil {
		logger.Info("用户[%s]不存在，开始创建", execUser)
		if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("useradd %s -g root -s /bin/bash -d /home/mysql",
			execUser)); err != nil {
			logger.Error("创建系统用户[%s]失败,%s, %v", execUser, output, err.Error())
			return err
		}
		logger.Info("用户[%s]创建成功", execUser)
	} else {
		logger.Info("用户[%s]存在, 跳过创建", execUser)
	}

	// mkdir
	extraCmd := fmt.Sprintf("mkdir -p %s ;mkdir -p %s ; mkdir -p %s", dataDir, envDir, logDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err)
		return err
	}

	// chown
	extraCmd = fmt.Sprintf("chown -R %s /data/vm* ; chown -R %s %s", execUser, execUser, dataDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Chown failed :%s", err)
		return err
	}
	logger.Info("修改系统参数")

	extraCmd = "cat >/etc/sysctl.d/vm.conf <<'EOF'\n" + "vm.max_map_count=2621440\n" +
		"fs.file-max=655360\n" + "EOF"
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Write vm.conf faild :%s", err)
		return err
	}

	extraCmd = "sysctl --system"
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("sysctl --system faild :%s", err)
		return err
	}

	extraCmd = fmt.Sprintf("cat > /etc/profile.d/vm.sh <<'EOF'\n"+
		"ulimit -n 512000\n"+
		"export VM_HOME=/data/vmenv/vm\n"+
		"export PATH=${VM_HOME}/bin:$PATH\n"+
		"export LOCAL_IP=%s\n"+
		"EOF", host)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Write vm.sh faild :%s", err)
		return err
	}

	extraCmd = "source /etc/profile"
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Exec [%s] faild :%s", extraCmd, err)
		return err
	}

	return nil
}

// InstallVMStorage TODO
/**
 * @description: 安装vmstorage
 * @return {*}
 */
func (i *InstallVMComp) InstallVMStorage() (err error) {

	vmc := vmutil.VMConfig{
		RetentionPeriod: i.Params.RetentionPeriod,
		StorageDataPath: i.Params.DataPath,
	}
	logger.Info("部署vmstorage开始...")
	if err := i.InstallVMBase(cst.VMStorage, i.Params.StorageConfig, vmc); err != nil {
		logger.Error("部署vmstorage失败. %s", err)
		return err
	}
	logger.Info("部署vmstorage结束...")

	return nil
}

// InstallVMInsert TODO
/**
 * @description: 安装vminsert
 * @return {*}
 */
func (i *InstallVMComp) InstallVMInsert() (err error) {
	vmc := vmutil.VMConfig{
		ReplicationFactor: i.Params.ReplicationFactor,
		StorageNode:       i.Params.StorageNode,
	}
	logger.Info("部署vminsert开始...")
	if err := i.InstallVMBase(cst.VMInsert, i.Params.InsertConfig, vmc); err != nil {
		logger.Error("部署vminsert失败. %s", err)
		return err
	}
	logger.Info("部署vminsert结束...")

	return nil
}

// InstallVMSelect TODO
/**
 * @description: 安装select
 * @return {*}
 */
func (i *InstallVMComp) InstallVMSelect() (err error) {

	vmc := vmutil.VMConfig{
		StorageNode: i.Params.StorageNode,
	}
	logger.Info("部署vmselect开始...")
	if err := i.InstallVMBase(cst.VMSelect, i.Params.SelectConfig, vmc); err != nil {
		logger.Error("部署vmselect失败. %s", err)
		return err
	}
	logger.Info("部署vmselect结束...")

	return nil
}

// InstallVMAuth 安装vmauth
func (i *InstallVMComp) InstallVMAuth() (err error) {
	version := i.Params.VMVersion
	// 需要提前建好软链
	vmBaseDir := fmt.Sprintf("%s/victoria-metrics-%s", cst.DefaultVMEnv, version)
	link := fmt.Sprintf("%s/vm", cst.DefaultVMEnv)
	extraCmd := fmt.Sprintf("ln -sf %s %s ", vmBaseDir, link)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link failed, %s", err)
		return err
	}
	// 要部署两个实例, 一个用于vminsert, 一个用于vmselect
	// ln -sf /data/vmenv/vm/bin/vmauth-prod  /data/vmenv/vm/bin/vmauth_insert-prod
	// ln -sf /data/vmenv/vmpack/bin/vmauth-prod  /data/vmenv/vm/bin/vmauth_select-prod
	vmPath := fmt.Sprintf("%s/victoria-metrics-%s/bin", cst.DefaultVMEnv, version)
	extraCmd = fmt.Sprintf("ln -sf %s/vmauth-prod %s/%s-prod ;", vmPath, vmPath, cst.VMAuthInsert) +
		fmt.Sprintf("ln -sf %s/vmauth-prod %s/%s-prod", vmPath, vmPath, cst.VMAuthSelect)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Exec [%s] faild :%s", extraCmd, err)
		return err
	}

	// write insert configfile
	content, err := vmutil.GenerateAuthYAML(i.Params.InsertNodes)
	if err != nil {
		return err
	}
	if err = os.WriteFile(cst.VMAuthInsertConf, content, 0644); err != nil {
		logger.Error("write %s failed, %s", cst.VMAuthInsertConf, err)
		return err
	}

	// write select configfile
	content, err = vmutil.GenerateAuthYAML(i.Params.SelectNodes)
	if err != nil {
		return err
	}
	if err = os.WriteFile(cst.VMAuthSelectConf, content, 0644); err != nil {
		logger.Error("write %s failed, %s", cst.VMAuthSelectConf, err)
		return err
	}

	// vmauth insert
	insertListenAddr := fmt.Sprintf("%s:%d", i.Params.Host, i.Params.InsertPort)
	vmc := vmutil.VMConfig{
		AuthConfig:     cst.VMAuthInsertConf,
		HTTPListenAddr: insertListenAddr,
	}
	logger.Info("部署vmauth_insert实例...")
	if err := i.InstallVMBase(cst.VMAuthInsert, i.Params.AuthConfig, vmc); err != nil {
		logger.Error("部署vmauth_insert失败. %s", err)
		return err
	}
	logger.Info("部署vmauth_insert结束...")
	// vmauth select
	selectListenAddr := fmt.Sprintf("%s:%d", i.Params.Host, i.Params.SelectPort)
	vmc = vmutil.VMConfig{
		AuthConfig:     cst.VMAuthSelectConf,
		HTTPListenAddr: selectListenAddr,
	}
	logger.Info("部署vmauth_select实例...")
	if err := i.InstallVMBase(cst.VMAuthSelect, i.Params.AuthConfig, vmc); err != nil {
		logger.Error("部署vmauth_select失败. %s", err)
		return err
	}
	logger.Info("部署vmauth_select结束...")

	return nil
}

// ReloadVMSelect 用于更新vmstorage之后要重启vmselect
func (i *InstallVMComp) ReloadVMSelect() (err error) {

	vmc := vmutil.VMConfig{
		StorageNode: i.Params.StorageNode,
	}
	logger.Info("重新配置vmselect...")
	if err := i.ReloadVmBase(cst.VMSelect, i.Params.SelectConfig, vmc); err != nil {
		logger.Error("Reload vmselect失败. %s", err)
		return err
	}
	logger.Info("Reload vmselect结束...")

	return nil
}

// ReloadVMInsert 用于更新vmstorage之后要重启vminsert
func (i *InstallVMComp) ReloadVMInsert() (err error) {

	vmc := vmutil.VMConfig{
		//		ReplicationFactor: i.Params.ReplicationFactor,
		StorageNode: i.Params.StorageNode,
	}
	logger.Info("重新配置vminsert...")
	if err := i.ReloadVmBase(cst.VMInsert, i.Params.InsertConfig, vmc); err != nil {
		logger.Error("Reload vminsert失败. %s", err)
		return err
	}
	logger.Info("Reload vminsert结束...")

	return nil
}

// ReloadVmBase 重新生成配置文件并重启
func (i *InstallVMComp) ReloadVmBase(role string, confJSON []byte, vmc vmutil.VMConfig) error {
	// 生成vmstorage_start.sh
	script := vmutil.VMRunScript(role, confJSON, vmc)
	// /data/vmenv/vm/vmstorage_start.sh
	scriptPath := fmt.Sprintf("%s/vm/%s_start.sh", cst.DefaultVMEnv, role)
	if err := os.WriteFile(scriptPath, script, 0644); err != nil {
		logger.Error("write %s failed, %s", scriptPath, err)
	}
	extraCmd := fmt.Sprintf("chmod +x %s", scriptPath)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec [%s] failed, %s", extraCmd, err)
		return err
	}
	// 保证目录都有权限
	extraCmd = fmt.Sprintf("chown -R %s /data/vm*", cst.DefaultExecUser)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec [%s] failed, %s", extraCmd, err)
		return err
	}
	// 重新启动该进程
	extraCmd = fmt.Sprintf("supervisorctl restart all")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec [%s] failed, %s", extraCmd, err)
		return err
	}
	// sleep等待进程拉起
	time.Sleep(30 * time.Second)
	return nil
}

// InstallVMBase 安装VM的基础方法
func (i *InstallVMComp) InstallVMBase(role string, confJSON []byte, vmc vmutil.VMConfig) error {
	version := i.Params.VMVersion

	// cd /data/vmenv,  ln -s /data/vmenv/victoria-metrics-1.99.0 /data/vmenv/vm
	vmBaseDir := fmt.Sprintf("%s/victoria-metrics-%s", cst.DefaultVMEnv, version)
	link := fmt.Sprintf("%s/vm", cst.DefaultVMEnv)
	extraCmd := fmt.Sprintf("ln -sf %s %s ", vmBaseDir, link)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link failed, %s, %s", output, err)
		return err
	}
	// 生成vmstorage_start.sh
	script := vmutil.VMRunScript(role, confJSON, vmc)
	// /data/vmenv/vm/vmstorage_start.sh
	scriptPath := fmt.Sprintf("%s/vm/%s_start.sh", cst.DefaultVMEnv, role)
	if err := os.WriteFile(scriptPath, script, 0644); err != nil {
		logger.Error("write %s failed, %s", scriptPath, err)
	}
	extraCmd = fmt.Sprintf("chmod +x %s", scriptPath)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec [%s] failed, %s", extraCmd, err)
		return err
	}

	// 生成vmstorage.ini
	vmini := vmutil.VMSuperIni(role, scriptPath)
	// /data/vmenv/supervisor/conf/vmstorage.ini
	iniPath := fmt.Sprintf("%s/%s.ini", cst.DefaultVMSupervisorConf, role)
	if err := os.WriteFile(iniPath, vmini, 0644); err != nil {
		logger.Error("write %s failed, %s", scriptPath, err)
	}
	// 保证目录都有权限
	extraCmd = fmt.Sprintf("chown -R %s /data/vm*", cst.DefaultExecUser)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec [%s] failed, %s", extraCmd, err)
		return err
	}
	if err := esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
		return err
	}

	return nil
}

// DecompressPkg TODO
/**
 * @description:  校验、解压es安装包
 * @return {*}
 */
func (i *InstallVMComp) DecompressPkg() (err error) {
	version := i.Params.VMVersion
	envDir := cst.DefaultVMEnv

	if err = os.Chdir(envDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", envDir, err)
	}
	pkgAbPath := fmt.Sprintf("%s/vmpack-%s.tar.gz", cst.DefaultPkgDir, version)
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s", pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}

	logger.Info("decompress vm pkg successfully")
	return nil
}

// InstallSupervisor TODO
/**
 * @description:  安装supervisor
 * @return {*}
 */
func (i *InstallVMComp) InstallSupervisor() (err error) {
	// Todo: check supervisor exist
	// supervisor

	envDir := cst.DefaultVMEnv
	execUser := cst.DefaultExecUser

	extraCmd := fmt.Sprintf("ln -sf %s %s", envDir+"/"+"supervisor/conf/supervisord.conf", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", envDir+"/"+"supervisor/bin/supervisorctl", "/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", envDir+"/"+"python/bin/supervisord", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", envDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// crontab
	crontabFile := fmt.Sprintf("crontab.%d", time.Now().Unix())
	extraCmd = fmt.Sprintf("crontab  -l -u %s >/home/%s/%s", execUser, execUser, crontabFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
	}

	extraCmd = fmt.Sprintf("cp /home/%s/%s /home/%s/crontab.tmp", execUser, crontabFile, execUser)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(`sed -i '/check_supervisord.sh/d' /home/%s/%s`, execUser, crontabFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("echo '*/1 * * * *  %s/check_supervisord.sh ", cst.DefaultVMSupervisorDir) +
		fmt.Sprintf(">>%s/check_supervisord.err 2>&1' >>/home/%s/%s", cst.DefaultVMSupervisorConf, execUser, crontabFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(`crontab -u %s /home/%s/%s`, execUser, execUser, crontabFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	startCmd := fmt.Sprintf(`su - mysql -c "/usr/local/bin/supervisord -c %s/supervisord.conf"`,
		cst.DefaultVMSupervisorConf)
	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}
