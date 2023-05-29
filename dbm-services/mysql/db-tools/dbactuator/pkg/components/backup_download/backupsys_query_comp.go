package backup_download

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/httpclient"
)

// IBSQueryComp TODO
type IBSQueryComp struct {
	Params IBSQueryParam `json:"extend"`
}

// IBSQueryParam download ibs-query
type IBSQueryParam struct {
	IBSQueryReq
	// ieg backup system url and auth params
	IBSInfo IBSBaseInfo `json:"ibs_info" validate:"required"`
	client  *httpclient.HttpClient
}

// Example TODO
func (c *IBSQueryComp) Example() interface{} {
	ibsReq := IBSQueryParam{
		IBSInfo: IBSBaseInfo{
			SysID:  "bkdbm",
			Key:    "fzLosxxxxxxxxxxxx",
			Ticket: "",
			Url:    "http://{{BACKUP_SERVER}}",
		},
		IBSQueryReq: IBSQueryReq{
			SourceIp:  "1.1.1.1",
			BeginDate: "2022-10-30 00:00:01",
			EndDate:   "2022-10-31 00:00:01",
			FileName:  "filename",
		},
	}
	return &IBSQueryComp{
		Params: ibsReq,
	}
}

// Init TODO
func (c *IBSQueryComp) Init() error {
	c.Params.client = &httpclient.HttpClient{
		Client: httpclient.New(),
		Url:    c.Params.IBSInfo.Url,
	}
	return nil
}

// PreCheck TODO
func (c *IBSQueryComp) PreCheck() error {
	return nil
}

// Start TODO
func (c *IBSQueryComp) Start() error {
	return c.Params.searchFiles()
}

func (r *IBSQueryParam) searchFiles() error {
	if resp, err := r.BsQuery(r.IBSQueryReq); err != nil {
		return err
	} else {
		return components.PrintOutputCtx(resp.Detail)
	}
}
