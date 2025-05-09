package mysql

import "github.com/pkg/errors"

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
func (c *MySQL) MonitorItemsConfig(ports ...int) ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/monitor_items_config", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call monitor_items_config")
	}

	return data, nil
}

func (c *MySQL) MonitorRuntimeConfig(ports ...int) ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/monitor_runtime_config", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call monitor_runtime_config")
	}
	return data, nil
}
