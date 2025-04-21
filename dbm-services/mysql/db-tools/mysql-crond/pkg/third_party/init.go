package third_party

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/third_party/instance_info_updater"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/third_party/nginx_updater"
	"errors"

	"github.com/robfig/cron/v3"
)

var ThirdPartyRegisters []func(cron *cron.Cron)

func init() {
	ThirdPartyRegisters = []func(*cron.Cron){
		nginx_updater.Register,
		instance_info_updater.Register,
	}
}

func Updater() (err error) {
	e := instance_info_updater.Updater()
	if e != nil {
		err = errors.Join(err, e)
	}

	e = nginx_updater.Updater()
	if e != nil {
		err = errors.Join(err, e)
	}

	return err
}
