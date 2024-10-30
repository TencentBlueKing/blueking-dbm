package common

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"strconv"
	"strings"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
)

// MongoComandResult mongo command result
type MongoComandResult struct {
	Ok int `json:"ok" bson:"ok"`
}

// RsConfResult rs config result
type RsConfResult struct {
	MongoComandResult
	Config RsConf `json:"config" bson:"config"`
}

// RsConf rs config
type RsConf struct {
	Id                                 string         `json:"_id" bson:"_id"`
	Version                            int            `json:"version,omitempty" bson:"version,omitempty"`
	Configsvr                          bool           `json:"configsvr,omitempty" bson:"configsvr,omitempty"`
	ProtocolVersion                    int            `json:"protocolVersion,omitempty" bson:"protocolVersion,omitempty"`
	WriteConcernMajorityJournalDefault bool           `json:"writeConcernMajorityJournalDefault,omitempty" bson:"writeConcernMajorityJournalDefault,omitempty"`
	Hosts                              []RsConfMember `json:"members" bson:"members"`
}

// RsConfMember rs config member
type RsConfMember struct {
	Id           int    `json:"_id" bson:"_id"`
	Host         string `json:"host" bson:"host"`
	ArbiterOnly  bool   `json:"arbiterOnly" bson:"arbiterOnly"`
	BuildIndexes bool   `json:"buildIndexes" bson:"buildIndexes"`
	Hidden       bool   `json:"hidden" bson:"hidden"`
	Priority     int    `json:"priority" bson:"priority"`
	Tags         struct {
	} `json:"tags" bson:"tags"`
	SlaveDelay int64 `json:"-" bson:"-"`
	Votes      int   `json:"votes" bson:"votes"`
}

// NewRsOp new a RsOp instance
func NewRsOp() *RsOp {
	return &RsOp{}
}

// RsOp rs operation
type RsOp struct {
}

// GetRsConf get rs config
// inst is the Instance of the mongo
// return the rs config, error if failed
func (rs *RsOp) GetRsConf(inst *Instance) (*RsConfResult, error) {
	client, err := inst.Connect()
	if err != nil {
		return nil, errors.Wrap(err, "connect to mongo")
	}
	var out = RsConfResult{}
	err = mymongo.RunCommand(client, "admin", "replSetGetConfig", 60, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

// ReConfig do rs.reconfig()
// inst is the Instance of the mongo
// val is the new value of the rs.conf
// timeoutSecond is the timeout of the command
func (rs *RsOp) ReConfig(inst *Instance, val *RsConf, timeoutSecond int64) (*MongoComandResult, error) {
	client, err := inst.Connect()
	if err != nil {
		return nil, errors.Wrap(err, "connect to mongo")
	}
	val.Version = val.Version + 1
	var out = MongoComandResult{}
	err = mymongo.RunCommandWithVal(client, "admin", "replSetReconfig", val, timeoutSecond, &out)
	if err != nil {
		return nil, errors.Wrap(err, "replSetReconfig")
	}
	return &out, nil
}

// SetPriority set priority
// inst is the Instance of the mongo
// member is the member to set
// priority is the new priority of the member, 0 means hidden
func (rs *RsOp) SetPriority(inst *Instance, member string, priority int) error {
	isMasterResult, err := inst.IsMaster()
	if err != nil {
		return errors.Wrap(err, "isMaster")
	}
	if isMasterResult.Primary == "" {
		return errors.New("not master")
	}
	primaryIp, primaryPort, err := splitHostPort(isMasterResult.Primary)
	if err != nil {
		return errors.Wrap(err, "splitHostPort")
	}

	primaryInst := NewInstance(primaryIp, primaryPort, inst.AdminUsername, inst.AdminPassword, "mongod")
	conf, err := rs.GetRsConf(primaryInst)
	if err != nil {
		return errors.Wrap(err, "GetRsConf")
	}

	found := false
	// set priority
	for i, m := range conf.Config.Hosts {
		if m.Host == member {
			found = true
			conf.Config.Hosts[i].Priority = priority
			if priority > 0 {
				conf.Config.Hosts[i].Hidden = false
				conf.Config.Hosts[i].Votes = 1
			}
		}
	}
	if !found {
		return errors.New("member not found")
	}

	out, err := rs.ReConfig(primaryInst, &conf.Config, 120)
	if err != nil {

		return errors.Wrap(err, "ReConfig")
	}
	if out.Ok != 1 {
		return errors.New("ReConfig failed")
	}
	return nil
}

// Initiate do rs.initiate()
// inst is the Instance of the mongo
// val is the new value of the rs.conf
// timeoutSecond is the timeout of the command
func (rs *RsOp) Initiate(inst *Instance, val *RsConf, timeoutSecond int64) (*MongoComandResult, error) {
	client, err := inst.ConnectDirect()
	if err != nil {
		return nil, errors.Wrap(err, "connect to mongo")
	}

	var out = MongoComandResult{}
	var members []bson.M
	for _, member := range val.Hosts {
		members = append(members, bson.M{
			"_id":  member.Id,
			"host": member.Host,
		})
	}
	config := bson.M{
		"_id":     val.Id,
		"members": members,
	}
	err = mymongo.RunAdminCommand(client, bson.M{"replSetInitiate": config}, timeoutSecond, &out)
	if err != nil {
		return nil, errors.Wrap(err, "replSetInitiate")
	}
	return &out, nil
}

// splitHostPort split host:port to host and port
// return error if bad addr
func splitHostPort(addr string) (string, int, error) {
	fs := strings.Split(addr, ":")
	if len(fs) != 2 {
		return "", 0, errors.New("bad addr")
	}
	port, err := strconv.Atoi(fs[1])
	if err != nil {
		return "", 0, errors.Wrap(err, "invalid port")
	}
	return fs[0], port, nil
}
