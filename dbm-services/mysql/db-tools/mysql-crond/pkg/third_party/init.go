package third_party

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/third_party/nginx_updater"

	"github.com/robfig/cron/v3"
)

var ThirdPartyRegisters []func(cron *cron.Cron)

func init() {
	ThirdPartyRegisters = []func(*cron.Cron){
		nginx_updater.Register,
	}
}
