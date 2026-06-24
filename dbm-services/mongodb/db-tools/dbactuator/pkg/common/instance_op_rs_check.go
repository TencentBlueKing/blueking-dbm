package common

import (
	"context"
	"fmt"
	"strings"

	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"

	"github.com/pkg/errors"
)

type rsStatusMember struct {
	Name     string `bson:"name"`
	Health   int    `bson:"health"`
	StateStr string `bson:"stateStr"`
}

type replSetGetStatusResult struct {
	Members []rsStatusMember `bson:"members"`
}

func isRsMemberReadyForRestart(stateStr string, health int) bool {
	if health != 1 {
		return false
	}
	switch stateStr {
	case "PRIMARY", "SECONDARY", "ARBITER":
		return true
	default:
		return false
	}
}

// ValidateRsAvailabilityBeforeRestart ensures every other RS member is healthy and that a strict
// majority of members would remain alive after this member restarts.
// ARBITER members count toward quorum; only PRIMARY/SECONDARY/ARBITER with health=1 are considered ready.
func ValidateRsAvailabilityBeforeRestart(members []rsStatusMember, selfAddr string) error {
	if len(members) == 0 {
		return errors.New("replSetGetStatus returned no members")
	}
	selfAddr = strings.TrimSpace(selfAddr)
	total := len(members)
	healthy := 0
	selfHealthy := false
	for _, m := range members {
		ready := isRsMemberReadyForRestart(m.StateStr, m.Health)
		if ready {
			healthy++
		}
		if m.Name == selfAddr {
			selfHealthy = ready
			continue
		}
		if !ready {
			return fmt.Errorf(
				"rs member %s is not healthy before restart (state=%s health=%d)",
				m.Name, m.StateStr, m.Health,
			)
		}
	}
	remaining := healthy
	if selfHealthy {
		remaining--
	}
	if remaining*2 <= total {
		return fmt.Errorf(
			"restarting %s would leave %d/%d rs members alive, strict majority required",
			selfAddr, remaining, total,
		)
	}
	return nil
}

// ValidateRsAllMembersReady ensures every RS member is PRIMARY, SECONDARY, or ARBITER with health=1.
func ValidateRsAllMembersReady(members []rsStatusMember) error {
	if len(members) == 0 {
		return errors.New("replSetGetStatus returned no members")
	}
	for _, m := range members {
		if !isRsMemberReadyForRestart(m.StateStr, m.Health) {
			return fmt.Errorf(
				"rs member %s is not ready after restart (state=%s health=%d)",
				m.Name, m.StateStr, m.Health,
			)
		}
	}
	return nil
}

// DoCheckRsAvailabilityBeforeRestart validates RS health/quorum before graceful restart.
func (inst *InstanceOp) DoCheckRsAvailabilityBeforeRestart() error {
	if strings.EqualFold(strings.TrimSpace(inst.InstanceType), "mongos") {
		inst.logger.Info("skip rs availability check for mongos %s", inst.Addr())
		return nil
	}
	client, err := inst.ConnectDirect()
	if err != nil {
		return errors.Wrap(err, "ConnectDirect for rs availability check")
	}
	defer client.Disconnect(context.Background())

	isMaster, err := mymongo.IsMaster(client, 60)
	if err != nil {
		return errors.Wrap(err, "isMaster for rs availability check")
	}
	if isMaster.Msg == "isdbgrid" || strings.TrimSpace(isMaster.SetName) == "" {
		inst.logger.Info("skip rs availability check for non-rs instance %s", inst.Addr())
		return nil
	}

	var status replSetGetStatusResult
	if err = mymongo.RunCommand(client, "admin", "replSetGetStatus", 60, &status); err != nil {
		return errors.Wrap(err, "replSetGetStatus for rs availability check")
	}
	inst.logger.Info("replSetGetStatus members=%d before restarting %s", len(status.Members), inst.Addr())
	return ValidateRsAvailabilityBeforeRestart(status.Members, inst.Addr())
}

// DoCheckRsAllMembersReady validates all RS members are PRIMARY/SECONDARY/ARBITER after rolling restart.
func (inst *InstanceOp) DoCheckRsAllMembersReady() error {
	if strings.EqualFold(strings.TrimSpace(inst.InstanceType), "mongos") {
		inst.logger.Info("skip rs all-members check for mongos %s", inst.Addr())
		return nil
	}
	client, err := inst.ConnectDirect()
	if err != nil {
		return errors.Wrap(err, "ConnectDirect for rs all-members check")
	}
	defer client.Disconnect(context.Background())

	isMaster, err := mymongo.IsMaster(client, 60)
	if err != nil {
		return errors.Wrap(err, "isMaster for rs all-members check")
	}
	if isMaster.Msg == "isdbgrid" || strings.TrimSpace(isMaster.SetName) == "" {
		inst.logger.Info("skip rs all-members check for non-rs instance %s", inst.Addr())
		return nil
	}

	var status replSetGetStatusResult
	if err = mymongo.RunCommand(client, "admin", "replSetGetStatus", 60, &status); err != nil {
		return errors.Wrap(err, "replSetGetStatus for rs all-members check")
	}
	inst.logger.Info("replSetGetStatus members=%d after rs restart on %s", len(status.Members), inst.Addr())
	return ValidateRsAllMembersReady(status.Members)
}
