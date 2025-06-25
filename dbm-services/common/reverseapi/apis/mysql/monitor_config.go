package mysql

import (
	"dbm-services/common/reverseapi/internal/core"

	"github.com/pkg/errors"
)

//MonitorItemsConfig
/*
`
	{
	    "20000": {
	      "character-consistency": {
	        "enable": true,
	        "machine_type": [
	          "single",
	          "backend",
	          "remote",
	          "spider"
	        ],
	        "name": "character-consistency",
	        "role": [],
	        "schedule": "0 0 14 * * 1"
	      },
		  ...
	    },
	    "20001": {
	      "character-consistency": {
	        "enable": true,
	        "machine_type": [
	          "single",
	          "backend",
	          "remote",
	          "spider"
	        ],
	        "name": "character-consistency",
	        "role": [],
	        "schedule": "0 0 14 * * 1"
	      },
		  ...
	    }
	  }
`
*/
func MonitorItemsConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/monitor_items_config/", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call monitor_items_config")
	}

	return data, nil
}

func MonitorRuntimeConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/monitor_runtime_config/", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call monitor_runtime_config")
	}
	return data, nil
}
