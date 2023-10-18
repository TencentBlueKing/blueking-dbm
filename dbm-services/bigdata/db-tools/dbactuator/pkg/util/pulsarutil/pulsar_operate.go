package pulsarutil

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/go-ini/ini"
	"github.com/shirou/gopsutil/v3/mem"
)

// GetMemSizeInMi TODO
func GetMemSizeInMi() (uint64, error) {
	vMem, err := mem.VirtualMemory()
	if err != nil {
		return 0, err
	}
	kilo := uint64(1024)
	totalMemInMi := vMem.Total / kilo / kilo
	return totalMemInMi, nil
}

// GetHeapAndDirectMemInMi TODO
func GetHeapAndDirectMemInMi() (string, string, error) {
	heapSize := "0g"
	directMem := "0g"
	systemMem, err := GetMemSizeInMi()
	if err != nil {
		return heapSize, directMem, err
	}

	if systemMem > 128*uint64(1024) {
		heapSize = "30g"
		directMem = "30g"
	} else {
		// heap + direct memory = 50% memory
		// heap : direct memory = 1 : 2
		heapSize = fmt.Sprintf("%vm", systemMem/6)
		directMem = fmt.Sprintf("%vm", systemMem/3)
	}

	return heapSize, directMem, nil
}

// SupervisorctlUpdate TODO
func SupervisorctlUpdate() error {
	startCmd := "supervisorctl update"
	logger.Info(fmt.Sprintf("exec %s", startCmd))
	_, err := osutil.RunInBG(false, startCmd)
	return err
}

// GenZookeeperIni TODO
func GenZookeeperIni() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:zookeeper]
command=%s/zookeeper/bin/pulsar zookeeper ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
stopsignal=KILL ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/pulsarenv/zookeeper/zookeeper_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`, cst.DefaultPulsarEnvDir))
	return iniRaw
}

// GenBookkeeperIni TODO
func GenBookkeeperIni() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:bookkeeper]
command=%s/bookkeeper/bin/pulsar bookie ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/pulsarenv/bookkeeper/bookkeeper_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`, cst.DefaultPulsarEnvDir))
	return iniRaw
}

// GenBrokerIni TODO
func GenBrokerIni() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:broker]
command=%s/broker/bin/pulsar broker ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/pulsarenv/broker/broker_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`, cst.DefaultPulsarEnvDir))
	return iniRaw
}

// GenPulsarManagerIni TODO
func GenPulsarManagerIni() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:pulsar-manager]
directory=%s ;
command=%s/bin/pulsar-manager ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=%s/pulsar-manager_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`, cst.DefaultPulsarManagerDir,
		cst.DefaultPulsarManagerDir, cst.DefaultPulsarManagerDir))
	return iniRaw
}

// SetBookieReadOnly 将bookie设置为只读
func SetBookieReadOnly() (err error) {
	bookieConfig, iniErr := ini.Load(cst.DefaultPulsarBkConf)
	if iniErr != nil {
		logger.Error("Failed to read file %s: %v", cst.DefaultPulsarBkConf, iniErr)
		return iniErr
	}

	section, secErr := bookieConfig.GetSection("")
	if secErr != nil {
		logger.Error("Failed to get section: %v", secErr)
		return secErr
	}

	if section.Haskey("readOnlyModeEnabled") {
		section.Key("readOnlyModeEnabled").SetValue("true")
	} else {
		_, keyErr := section.NewKey("readOnlyModeEnabled", "true")
		if keyErr != nil {
			logger.Error("Failed to add readOnlyModeEnabled : %v", keyErr)
			return keyErr
		}
	}
	if section.Haskey("forceReadOnlyBookie") {
		section.Key("forceReadOnlyBookie").SetValue("true")
	} else {
		_, keyErr := section.NewKey("forceReadOnlyBookie", "true")
		if keyErr != nil {
			logger.Error("Failed to add forceReadOnlyBookie : %v", keyErr)
			return keyErr
		}
	}

	iniErr = bookieConfig.SaveTo(cst.DefaultPulsarBkConf)
	if iniErr != nil {
		logger.Error("Failed to save file %s: %v", cst.DefaultPulsarBkConf, iniErr)
		return iniErr
	}

	return nil
}

// UnsetBookieReadOnly 取消bookie只读状态
func UnsetBookieReadOnly() (err error) {
	bookieConfig, iniErr := ini.Load(cst.DefaultPulsarBkConf)
	if iniErr != nil {
		logger.Error("Failed to read file %s: %v", cst.DefaultPulsarBkConf, iniErr)
		return iniErr
	}

	section, secErr := bookieConfig.GetSection("")
	if secErr != nil {
		logger.Error("Failed to get section: %v", secErr)
		return secErr
	}

	if section.Haskey("forceReadOnlyBookie") {
		section.Key("forceReadOnlyBookie").SetValue("false")
	} else {
		_, keyErr := section.NewKey("forceReadOnlyBookie", "false")
		if keyErr != nil {
			logger.Error("Failed to add forceReadOnlyBookie : %v", keyErr)
			return keyErr
		}
	}

	iniErr = bookieConfig.SaveTo(cst.DefaultPulsarBkConf)
	if iniErr != nil {
		logger.Error("Failed to save file %s: %v", cst.DefaultPulsarBkConf, iniErr)
		return iniErr
	}

	return nil
}
