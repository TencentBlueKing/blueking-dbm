package atomsys

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// ExporterParams
type ExporterParams struct {
	IP           string         `json:"ip" validate:"required"`
	MetaRole     string         `json:"role" validate:"required"`
	Ports        []int          `json:"ports"`
	Password     string         `json:"password"`
	ImmuteDomain string         `json:"cluster_domain"`
	PasswordMap  map[int]string `json:"password_map"`
	ClusterType  string         `json:"cluster_type"`
}

// ChangePwd atomjob
type RestartExporter struct {
	runtime *jobruntime.JobGenericRuntime
	params  ExporterParams

	errChan chan error
}

// NewRestartExporter
func NewRestartExporter() jobruntime.JobRunner {
	return &RestartExporter{}
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RestartExporter)(nil)

// Init 初始化
func (job *RestartExporter) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("ChangePwd Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ChangePwd Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RestartExporter) Name() string {
	return "restart_exporter"
}

// Run 执行
func (job *RestartExporter) Run() (err error) {
	exporterProcessName := "dbm_redis_exporter"
	if job.params.MetaRole == consts.MetaRolePredixy {
		exporterProcessName = "dbm_predixy_exporter"
	} else if job.params.MetaRole == consts.MetaRoleTwemproxy {
		exporterProcessName = "dbm_twemproxy_exporter"
	}

	if job.params.ClusterType == consts.TendisTypeRedisInstance {
		for port, password := range job.params.PasswordMap {
			job.runtime.Logger.Info("regenerate exporter config 4 instance :%d", port)
			// del first .
			common.DeleteExporterConfigFile(port)
			// re generate it .
			common.CreateLocalExporterConfigFile(job.params.IP, port, job.params.MetaRole, password)
		}
	} else {
		// send kill exporter
		for _, port := range job.params.Ports {
			job.runtime.Logger.Info("regenerate exporter config 4 instance :%d", port)
			// del first .
			common.DeleteExporterConfigFile(port)
			// re generate it .
			common.CreateLocalExporterConfigFile(job.params.IP, port, job.params.MetaRole, job.params.Password)
		}
	}

	// kill all exporter, and clean its GSE plugin work directory (safely).
	// 安全策略（多重"安全码"）：
	// 1) 遍历 /proc/*/exe 与 /proc/*/cmdline，用完整 exporter 名精确匹配进程；
	//    (不能用 pgrep -x，因为 Linux comm 名最长 15 字节，dbm_twemproxy_exporter 会被截断)
	// 2) 用 readlink /proc/<pid>/cwd 取真实 cwd（进程死了就读不到，所以在 kill 之前先记录）；
	// 3) 白名单：cwd 必须匹配正则 ^/usr/local/gse2_bkte/external_plugins/sub_[0-9]+_service_[0-9]+/<exporter名>$
	//    完全锁死到 GSE Agent 插件目录结构，无关目录一律拒绝；
	// 4) kill 之后再执行 rm -rf，确保先干掉进程再删目录，避免文件被占用。
	job.runtime.Logger.Info("try restart exporter: record cwd -> killall -> clean dir.")
	pattern := fmt.Sprintf(`^/usr/local/gse2_bkte/external_plugins/sub_[0-9]+_service_[0-9]+/%s$`, exporterProcessName)
	cleanCmd := fmt.Sprintf(`
		set +e
		# step1: 在 kill 之前，先通过 /proc 精确定位 exporter 进程并记录 cwd
		# 注意：不能用 pgrep -x, 因为 comm 名最长 15 字节会被截断
		tmpfile=$(mktemp /tmp/exporter_cwd.XXXXXX)
		found_any=0
		for procdir in /proc/[0-9]*; do
			pid=$(basename "${procdir}")
			# 通过 exe 软链取真实可执行文件路径, 精确匹配文件名
			exe=$(readlink "${procdir}/exe" 2>/dev/null)
			if [ -z "${exe}" ]; then
				continue
			fi
			exe_base=$(basename "${exe}")
			if [ "${exe_base}" != "%s" ]; then
				continue
			fi
			found_any=1
			cwd=$(readlink "${procdir}/cwd" 2>/dev/null)
			if [ -z "${cwd}" ]; then
				echo "[clean-exporter] skip pid=${pid}: empty cwd (exe=${exe})"
				continue
			fi
			# 白名单：必须严格匹配 GSE external_plugins 目录格式
			if echo "${cwd}" | grep -Eq '%s'; then
				echo "[clean-exporter] record pid=${pid} exe=${exe} cwd=${cwd}"
				echo "${cwd}" >> "${tmpfile}"
			else
				echo "[clean-exporter] skip pid=${pid} cwd=${cwd}: not match gse external_plugins pattern"
			fi
		done
		if [ "${found_any}" = "0" ]; then
			echo "[clean-exporter] no running process named %s found"
		fi

		# step2: killall -9
		echo "[clean-exporter] killall -9 %s"
		killall -9 %s 2>/dev/null || true
		sleep 1

		# step3: 对通过安全校验的 cwd 执行 rm -rf
		if [ -s "${tmpfile}" ]; then
			sort -u "${tmpfile}" | while read -r dir; do
				# 再次二次校验，防御性
				if echo "${dir}" | grep -Eq '%s'; then
					echo "[clean-exporter] clean dir=${dir}"
					rm -rf "${dir}"
					if [ $? -eq 0 ]; then
						echo "[clean-exporter] rm ok dir=${dir}"
					else
						echo "[clean-exporter] rm fail dir=${dir}"
					fi
				else
					echo "[clean-exporter] skip dir=${dir}: not match pattern (double check)"
				fi
			done
		else
			echo "[clean-exporter] no exporter cwd recorded, nothing to clean."
		fi
		rm -f "${tmpfile}"
`, exporterProcessName, pattern, exporterProcessName, exporterProcessName, exporterProcessName, pattern)
	cleanOut, err := util.RunBashCmd(cleanCmd, "", nil, 30*time.Second)
	if cleanOut != "" {
		// 把 shell 里 echo 出来的每一步动作都写到 job Logger, 方便审计"删了哪些目录"
		for _, line := range strings.Split(strings.TrimRight(cleanOut, "\n"), "\n") {
			if line == "" {
				continue
			}
			job.runtime.Logger.Info("%s", line)
		}
	}
	if err != nil {
		job.runtime.Logger.Warn("restart & clean exporter maybe failed : %+v", err)
	}

	job.runtime.Logger.Info("try reload bkmonitorbeat;bkunifylogbeat plugin...")
	if _, err := util.RunBashCmd("/usr/local/gse2_bkte/plugins/bin/reload.sh bkmonitorbeat",
		"", nil, 10*time.Second); err != nil {
		job.runtime.Logger.Warn("reload bkmonitorbeat maybe failed : %+v", err)
	}

	if _, err := util.RunBashCmd("/usr/local/gse2_bkte/plugins/bin/reload.sh bkunifylogbeat",
		"", nil, 10*time.Second); err != nil {
		job.runtime.Logger.Warn("reload bkunifylogbeat maybe failed : %+v", err)
	}
	job.runtime.Logger.Info("job done.^_^")
	return nil
}

// Retry times
func (job *RestartExporter) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RestartExporter) Rollback() error {
	return nil
}
